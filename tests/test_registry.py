"""Tests for FastMCP tool registration."""

from __future__ import annotations

from pal.tools.registry import build_server_instructions, mcp, run_pal_command


class TestToolRegistration:
    """Verify all tools are registered on the FastMCP instance."""

    def test_mcp_instance_exists(self) -> None:
        """FastMCP instance is created with correct name."""
        assert mcp.name == "pal-server"

    def test_all_tools_registered(self) -> None:
        """All 6 tools are registered."""
        tool_names = set(mcp._tool_manager._tools)
        expected = {
            "run_pal_command",
            "list_pal_commands",
            "read_pal_resource",
            "list_pal_resources",
            "pal_curl",
            "parse_pipeline",
        }
        assert expected == tool_names

    def test_run_pal_command_schema(self) -> None:
        """run_pal_command has correct input schema."""
        tool = mcp._tool_manager._tools["run_pal_command"]
        schema = tool.parameters
        assert "command" in schema.get("properties", {})
        assert "command" in schema.get("required", [])

    def test_parse_pipeline_schema(self) -> None:
        """parse_pipeline has required `command` string parameter."""
        tool = mcp._tool_manager._tools["parse_pipeline"]
        schema = tool.parameters
        assert "command" in schema.get("properties", {})
        assert "command" in schema.get("required", [])

    def test_parse_pipeline_description_documents_grammar(self) -> None:
        """parse_pipeline's description names every operator and the `--` marker.

        This is the *canonical* grammar reference exposed to the LLM, so the
        description must mention each piece — otherwise the LLM can't apply
        the rules.
        """
        tool = mcp._tool_manager._tools["parse_pipeline"]
        description = (tool.description or "").lower()
        for token in ("|", "&&", ";", "--"):
            assert token in description, f"missing {token!r} in description"

    def test_pal_curl_has_timeout_default(self) -> None:
        """pal_curl has timeout parameter with default."""
        tool = mcp._tool_manager._tools["pal_curl"]
        schema = tool.parameters
        props = schema.get("properties", {})
        assert "command" in props
        assert "timeout" in props

    def test_mcp_instructions_wired_to_server_instructions(self) -> None:
        """FastMCP was constructed with the computed SERVER_INSTRUCTIONS string."""
        from pal.tools.registry import SERVER_INSTRUCTIONS

        assert mcp.instructions == SERVER_INSTRUCTIONS

    def test_build_server_instructions_instructions_includes_protocol(self) -> None:
        """'instructions' mode (default) includes the protocol body."""
        built = build_server_instructions("instructions")
        assert "run_pal_command" in built
        assert "$$echo" in built
        assert "Executing Prompt-Based Commands" in built

    def test_build_server_instructions_per_call_omits_protocol(self) -> None:
        """'per-call' mode strips the protocol from the instructions string."""
        built = build_server_instructions("per-call")
        assert "run_pal_command" in built  # call-out kept
        assert "$$echo" not in built  # protocol stripped
        assert "Executing Prompt-Based Commands" not in built

    def test_build_server_instructions_both_includes_protocol(self) -> None:
        """'both' mode keeps the protocol in the instructions string."""
        built = build_server_instructions("both")
        assert "run_pal_command" in built
        assert "$$echo" in built
        assert "Executing Prompt-Based Commands" in built


class TestRunPalCommandRejectsPipelines:
    """run_pal_command must refuse multi-stage strings and direct the
    caller (the LLM) to parse_pipeline first.

    We only assert against the rejection path (which never touches ctx),
    so passing ctx=None is safe — the guard fires before any ctx access.
    The "raw-mode commands are NOT rejected" case is covered by the
    is_pipeline unit tests in tests/test_pipeline.py (Task 5), so we
    don't repeat it here.
    """

    async def test_rejects_pipe(self) -> None:
        result = await run_pal_command(command="a | b", ctx=None)  # type: ignore[arg-type]
        assert "parse_pipeline" in result
        assert "pipeline" in result.lower()

    async def test_rejects_and(self) -> None:
        result = await run_pal_command(command="a && b", ctx=None)  # type: ignore[arg-type]
        assert "parse_pipeline" in result

    async def test_rejects_seq(self) -> None:
        result = await run_pal_command(command="a ; b", ctx=None)  # type: ignore[arg-type]
        assert "parse_pipeline" in result
