from __future__ import annotations

from backend.core.query.analyzer import QueryAnalysis


class PromptBuilder:
    """Builds prompts for the LLM based on query analysis and context.

    Constructs a system prompt tailored to the query intent and
    a user prompt that includes the retrieved context and the
    original question.
    """

    def build_system_prompt(self, analysis: QueryAnalysis) -> str:
        """Build a system prompt based on the query analysis.

        Args:
            analysis: The query analysis result.

        Returns:
            A system-level instruction prompt.
        """
        intent_instructions = self._get_intent_instructions(analysis.intent)

        return (
            "You are RepoMind, an expert code intelligence assistant. "
            "You help developers understand code repositories.\n\n"
            f"INTENT: {analysis.intent}\n\n"
            f"{intent_instructions}\n\n"
            "RULES:\n"
            "- Answer based ONLY on the provided context.\n"
            "- If the context does not contain enough information, say so.\n"
            "- Cite specific file names, class names, and function names.\n"
            "- Use code blocks when showing code snippets.\n"
            "- Be concise but thorough.\n"
            "- Do not make up APIs or features that are not in the context."
        )

    def build_user_prompt(
        self,
        question: str,
        context: str,
        analysis: QueryAnalysis,
    ) -> str:
        """Build a user prompt with context and question.

        Args:
            question: The original user question.
            context: The retrieved and formatted context.
            analysis: The query analysis result.

        Returns:
            A formatted user prompt.
        """
        if not context:
            return (
                f"Question: {question}\n\n"
                "Note: No relevant context was found in the repository. "
                "Please answer based on your general knowledge if possible."
            )

        return (
            f"Repository Context:\n"
        )

    def build_full_prompt(
        self,
        question: str,
        context: str,
        analysis: QueryAnalysis,
    ) -> tuple[str, str]:
        """Build both system and user prompts.

        Args:
            question: The original user question.
            context: The retrieved and formatted context.
            analysis: The query analysis result.

        Returns:
            A tuple of (system_prompt, user_prompt).
        """
        system = self.build_system_prompt(analysis)

        if not context:
            user = (
                f"Question: {question}\n\n"
                "Note: No relevant context was found in the repository. "
                "Please answer based on your general knowledge if possible."
            )
        else:
            user = (
                f"Repository Context:\n{context}\n\n"
                f"Question: {question}\n\n"
                "Based on the context above, answer the question. "
                "Cite specific file names and code elements."
            )

        return system, user

    @staticmethod
    def _get_intent_instructions(intent: str) -> str:
        """Get specific instructions based on query intent."""
        instructions = {
            "explain_code": (
                "Explain what the relevant code does, its purpose, and how it works. "
                "Break down complex logic and mention key functions and classes."
            ),
            "find_function": (
                "Help the user locate the relevant code. "
                "Provide the exact file path, line numbers, and function/class names. "
                "Explain what each relevant symbol does."
            ),
            "architecture": (
                "Describe the high-level architecture and structure. "
                "Explain how different modules, classes, and files relate to each other. "
                "Mention key design patterns or architectural decisions visible in the code."
            ),
            "usage_example": (
                "Provide usage examples based on the code. "
                "Show how to call functions, instantiate classes, or use the API. "
                "Include code snippets with example inputs and expected behaviour."
            ),
            "implementation": (
                "Help understand how to implement or modify the code. "
                "Explain the current implementation and suggest patterns to follow. "
                "Mention relevant files that would need to be changed."
            ),
            "comparison": (
                "Compare the relevant code elements. "
                "Highlight differences in implementation, behaviour, or purpose. "
                "Mention pros and cons where applicable."
            ),
            "debugging": (
                "Help identify potential issues in the code. "
                "Look for error handling, edge cases, and common pitfalls. "
                "Suggest fixes or improvements based on the context."
            ),
            "general": (
                "Answer the question based on the provided context. "
                "Be helpful and precise about code elements."
            ),
        }
        return instructions.get(intent, instructions["general"])