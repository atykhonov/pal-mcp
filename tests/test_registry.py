"""Tests for FastMCP tool registration."""

from __future__ import annotations

from pal.tools.registry import mcp


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

    def test_server_instructions(self) -> None:
        """Server instructions are set."""
        assert "$$" in (mcp.instructions or "")
