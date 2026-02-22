"""MCP prompt definitions for common AT Protocol tasks."""

from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """Register reusable prompt templates for AT Protocol tasks."""

    @mcp.prompt()
    def explain_lexicon(nsid: str) -> str:
        """Explain an AT Protocol lexicon in detail.

        Retrieves the lexicon schema and provides a comprehensive explanation
        including its type, purpose, required fields, relationships to other
        lexicons, and practical usage examples.

        Args:
            nsid: The NSID of the lexicon to explain (e.g. "app.bsky.feed.post").
        """
        return (
            f"Please explain the AT Protocol lexicon '{nsid}' in detail.\n\n"
            f"First, use the get_lexicon tool to retrieve the full schema for '{nsid}'.\n"
            f"Then explain:\n"
            f"1. What this lexicon represents and its purpose in the AT Protocol\n"
            f"2. Whether it's a record type, query, procedure, or subscription\n"
            f"3. All required and optional fields with their types and constraints\n"
            f"4. How it relates to other lexicons (cross-references)\n"
            f"5. Practical examples of how this lexicon is used\n"
            f"6. Common patterns and best practices when working with it\n\n"
            f"If relevant, also search for related documentation using "
            f"search_atproto_docs to provide additional context."
        )

    @mcp.prompt()
    def implement_feature(description: str) -> str:
        """Get implementation guidance for an AT Protocol feature.

        Searches the cookbook, documentation, and lexicons to recommend
        the best approach for implementing a specific feature, complete
        with code examples and relevant API references.

        Args:
            description: Description of the feature to implement
                         (e.g. "create a bot that auto-replies to mentions",
                         "build an OAuth login flow", "subscribe to the firehose").
        """
        return (
            f"I want to implement the following feature using the AT Protocol / Bluesky API:\n\n"
            f"'{description}'\n\n"
            f"Please help me by:\n\n"
            f"1. First, search the cookbook examples using search_atproto_docs with "
            f'source="cookbook" to find relevant starter projects and implementation patterns.\n'
            f"2. Search the Bluesky API docs using search_bsky_api for relevant guides "
            f"and tutorials.\n"
            f"3. Look up any relevant lexicons using search_lexicons to understand the "
            f"data structures and endpoints involved.\n"
            f"4. If specific cookbook examples are found, retrieve them with "
            f"get_cookbook_example for full source code.\n\n"
            f"Based on what you find, provide:\n"
            f"- A recommended implementation approach\n"
            f"- The specific lexicons/endpoints needed\n"
            f"- Code examples (preferring cookbook patterns where available)\n"
            f"- Authentication requirements\n"
            f"- Any gotchas or best practices to be aware of"
        )

    @mcp.prompt()
    def debug_atproto(error: str) -> str:
        """Help debug an AT Protocol or Bluesky API issue.

        Searches docs and lexicons to diagnose errors and suggest fixes.

        Args:
            error: The error message, unexpected behavior, or issue description
                   (e.g. "InvalidToken error on createRecord", "firehose connection drops after 30s").
        """
        return (
            f"I'm encountering this issue with the AT Protocol / Bluesky API:\n\n"
            f"'{error}'\n\n"
            f"Please help me debug this by:\n\n"
            f"1. Search the documentation using search_atproto_docs for information "
            f"about this error or behavior.\n"
            f"2. Search Bluesky API docs using search_bsky_api for any known issues, "
            f"rate limits, or common mistakes.\n"
            f"3. Look up relevant lexicons using search_lexicons to verify the correct "
            f"request/response schemas.\n"
            f"4. Check the cookbook for working examples that demonstrate the correct approach.\n\n"
            f"Based on your findings, explain:\n"
            f"- What is likely causing this issue\n"
            f"- The correct way to handle this scenario\n"
            f"- A code fix or workaround\n"
            f"- Any relevant documentation links"
        )

    @mcp.prompt()
    def explore_namespace(namespace: str) -> str:
        """Explore all lexicons within an AT Protocol namespace.

        Lists and explains all lexicons under a given namespace prefix,
        showing how they relate to each other.

        Args:
            namespace: The namespace prefix to explore
                       (e.g. "app.bsky.feed", "com.atproto.repo", "chat.bsky").
        """
        return (
            f"Please explore the AT Protocol namespace '{namespace}'.\n\n"
            f"1. Use list_lexicons with namespace='{namespace}' to see all "
            f"lexicons in this namespace.\n"
            f"2. For each lexicon found, briefly describe its purpose and type "
            f"(record, query, procedure, etc.).\n"
            f"3. Explain how the lexicons in this namespace work together.\n"
            f"4. Show the typical workflow or data flow between these lexicons.\n"
            f"5. Provide practical examples of how this namespace is used.\n\n"
            f"Also search the documentation using search_atproto_docs for any "
            f"guides or tutorials related to this namespace."
        )
