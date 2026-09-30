# Framework Compliance (TC) tests — docs/03_test_spec.md TC-01..TC-11.
# Generic checks applied across all concrete nodes under src/nodes/ and the
# State schema, discovered dynamically rather than hardcoded per node.

import ast
import importlib
import inspect
import os
import pkgutil

import pytest

from framework.errors import SecurityViolationError
from framework.nodes.function_node import FunctionNode
from framework.schemas.trust_level import TrustLevel


def _discover_function_nodes() -> list[type]:
    pkg = importlib.import_module("src.nodes")
    discovered = []
    for _, modname, _ in pkgutil.walk_packages(pkg.__path__, prefix="src.nodes."):
        module = importlib.import_module(modname)
        for attr in vars(module).values():
            if (
                isinstance(attr, type)
                and issubclass(attr, FunctionNode)
                and attr is not FunctionNode
                and attr.__module__ == modname
            ):
                discovered.append(attr)
    return discovered


NODE_CLASSES = _discover_function_nodes()


# TC-01: State contract — flat TypedDict, no Pydantic/dataclass.


def test_tc01_state_is_flat_typeddict():
    from src.schemas.state import State

    assert not hasattr(State, "__pydantic_model__")
    assert not hasattr(State, "__dataclass_fields__")


# TC-02: SecurityViolationError fires on invalid input.


def test_tc02_security_violation_error_raised_on_invalid_input():
    from src.nodes.pre_process_node import PreProcessNode

    node = PreProcessNode()
    with pytest.raises(SecurityViolationError):
        node._extra_security_gate_input({"user_input": "x" * 2001})


# TC-03: No JWT/credential-named fields in State.


def test_tc03_no_credential_fields_in_state():
    import re

    state_file = os.path.join(os.path.dirname(__file__), "..", "..", "src", "schemas", "state.py")
    pattern = re.compile(r"(jwt|token|api_key|secret|password|credential|connection_string)", re.IGNORECASE)
    with open(state_file) as f:
        tree = ast.parse(f.read())
    violations = [
        item.target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        for item in node.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and pattern.search(item.target.id)
    ]
    assert violations == []


# TC-05: no duplicate lifecycle events (node_start/node_complete/node_error)
# emitted from inside execute() bodies.


@pytest.mark.parametrize("node_cls", NODE_CLASSES, ids=lambda c: c.__name__)
def test_tc05_no_duplicate_lifecycle_events_in_execute_source(node_cls):
    source = inspect.getsource(node_cls.execute)
    for forbidden in ("node_start", "node_complete", "node_error"):
        assert f'"{forbidden}"' not in source and f"'{forbidden}'" not in source, (
            f"{node_cls.__name__}.execute() must not emit lifecycle event {forbidden!r} — "
            "BaseNode.__call__() already emits it."
        )


# TC-06 / TC-07: @final gates cannot be overridden — TypeError at class def.


def test_tc06_overriding_security_gate_input_raises_typeerror():
    with pytest.raises(TypeError):

        class BadInputNode(FunctionNode):
            def _security_gate_input(self, state):
                return state

            def execute(self, state):
                return {}


def test_tc07_overriding_security_gate_output_raises_typeerror():
    with pytest.raises(TypeError):

        class BadOutputNode(FunctionNode):
            def _security_gate_output(self, result):
                return result

            def execute(self, state):
                return {}


# TC-08: required_trust_level enforced — insufficient trust is refused.


@pytest.mark.parametrize("node_cls", NODE_CLASSES, ids=lambda c: c.__name__)
def test_tc08_insufficient_trust_is_refused(node_cls):
    if node_cls.required_trust_level == TrustLevel.ANONYMOUS:
        pytest.skip(f"{node_cls.__name__} requires only ANONYMOUS — nothing lower to test")
    node = node_cls()
    state = {
        "caller_trust_level": TrustLevel.ANONYMOUS.value,
        "correlation_id": "tc08-test",
    }
    result = node(state)
    from framework.schemas.agent_status import AgentStatus

    assert result["status"] == AgentStatus.ERROR.value
    assert "S-1" in result["error_log"][0]


# TC-09 / TC-10: domain gate hooks are non-trivial (not bare `return state`/`pass`).


def test_tc09_pre_process_extra_input_gate_is_non_trivial():
    from src.nodes.pre_process_node import PreProcessNode

    source = inspect.getsource(PreProcessNode._extra_security_gate_input)
    assert "MAX_INPUT_CHARS" in source or "raise" in source


def test_tc10_post_process_extra_output_gate_is_non_trivial():
    from src.nodes.post_process_node import PostProcessNode

    source = inspect.getsource(PostProcessNode._extra_security_gate_output)
    assert "raise" in source


# TC-11: at least one domain emit_trace_event() call inside each execute().


@pytest.mark.parametrize("node_cls", NODE_CLASSES, ids=lambda c: c.__name__)
def test_tc11_domain_trace_event_emitted_in_execute(node_cls):
    source = inspect.getsource(node_cls.execute)
    assert "emit_trace_event(" in source, f"{node_cls.__name__}.execute() must call emit_trace_event()"
