# PB-1: BaseNode -> EventEmitter boundary.
# emit_trace_event() must fire on every invocation path (success and error),
# with no silent failures, for every concrete node under src/nodes/.

import importlib
import pkgutil

import pytest

from framework.schemas.trust_level import TrustLevel


def _discover_function_nodes() -> list[type]:
    from framework.nodes.function_node import FunctionNode

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


@pytest.mark.parametrize("node_cls", NODE_CLASSES, ids=lambda c: c.__name__)
def test_pb1_node_start_and_complete_events_fire_on_call(node_cls, monkeypatch):
    events: list[str] = []
    import framework.nodes.base_node as base_node_module

    monkeypatch.setattr(
        base_node_module,
        "emit_trace_event",
        lambda event_type, _payload, _state: events.append(event_type),
    )
    monkeypatch.setenv("USE_MOCK", "true")

    node = node_cls()
    state = {
        "caller_trust_level": node_cls.required_trust_level.value,
        "correlation_id": "pb1-test",
        "session_id": "pb1-session",
        "thread_id": "pb1-thread",
        "trace_id": "pb1-trace",
    }
    node(state)

    assert "node_start" in events, f"{node_cls.__name__}: node_start not emitted — silent failure"
    assert any(
        e in events for e in ("node_complete", "node_error")
    ), f"{node_cls.__name__}: neither node_complete nor node_error emitted — silent failure"


def test_pb1_s1_denial_still_emits_audit_event(monkeypatch):
    """Even a trust-gate denial (before execute()) must be audited, not silent."""
    from src.nodes.pre_process_node import PreProcessNode

    events: list[str] = []
    import framework.nodes.base_node as base_node_module

    monkeypatch.setattr(
        base_node_module,
        "emit_trace_event",
        lambda event_type, _payload, _state: events.append(event_type),
    )

    node = PreProcessNode()
    state = {"caller_trust_level": TrustLevel.ANONYMOUS.value, "correlation_id": "pb1-denial-test"}
    node(state)

    assert "s1_denied" in events
