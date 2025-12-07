"""
Mock components for end-to-end testing without LLM calls.
These components generate random structured content to test the Notion upload pipeline.
"""

import os
import random
import logging
from datetime import datetime
from typing import TypedDict
from pathlib import Path
from . import utils

# Configure logging
logger = logging.getLogger(__name__)


class MockImageTextExtractor:
    """Mock image text extractor that generates random text instead of calling GPT-4o-mini."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.text = ""

    def extract_text(self) -> str:
        """Generate mock extracted text based on images found in the directory."""
        images_path = utils.get_file_paths(self.repo_path)
        image_count = sum(1 for path in images_path if ".gitkeep" not in path)

        logger.info(f"[TEST MODE] Found {image_count} images in {self.repo_path}")
        logger.info("[TEST MODE] Generating random mock text (no LLM calls)")

        # Generate random structured content
        mock_content = self._generate_random_content(image_count)
        self.text = mock_content.strip()
        return self.text

    def _generate_random_content(self, image_count: int) -> str:
        """Generate random structured content for testing."""
        # Random topics
        topics = [
            "Intelligence Artificielle", "Machine Learning", "Blockchain",
            "Cybersécurité", "Cloud Computing", "Internet des Objets",
            "Réalité Virtuelle", "Big Data", "DevOps", "Quantum Computing"
        ]

        # Random section titles
        section_templates = [
            "Introduction", "Concepts Fondamentaux", "Applications Pratiques",
            "Défis et Perspectives", "Tendances Actuelles", "Technologies Émergentes",
            "Meilleures Pratiques", "Cas d'Usage"
        ]

        # Random sentences
        intro_sentences = [
            "est un domaine fascinant qui révolutionne notre quotidien.",
            "transforme la façon dont nous travaillons et vivons.",
            "représente une avancée technologique majeure de notre époque.",
            "ouvre de nouvelles possibilités dans de nombreux secteurs.",
            "est au cœur de la transformation numérique actuelle."
        ]

        description_sentences = [
            "Cette technologie combine innovation et créativité.",
            "Les applications sont vastes et en constante évolution.",
            "L'impact sur l'industrie est considérable.",
            "De nombreuses entreprises investissent massivement dans ce domaine.",
            "Les experts prévoient une croissance exponentielle."
        ]

        # Random bullet points
        bullet_topics = [
            ["Automatisation", "Optimisation", "Scalabilité"],
            ["Sécurité", "Performance", "Fiabilité"],
            ["Innovation", "Collaboration", "Agilité"],
            ["Analyse prédictive", "Traitement en temps réel", "Visualisation"],
            ["Infrastructure", "Architecture", "Intégration"]
        ]

        challenges = [
            ["Complexité technique", "Coûts d'implémentation", "Formation des équipes"],
            ["Sécurité des données", "Conformité réglementaire", "Éthique"],
            ["Scalabilité", "Maintenance", "Migration"],
            ["Adoption utilisateur", "Intégration legacy", "ROI"]
        ]

        # Select random elements
        topic = random.choice(topics)
        sections = random.sample(section_templates, k=min(4, len(section_templates)))

        # Build content
        content_parts = []

        for i, section in enumerate(sections, 1):
            content_parts.append(f"{i}. {section}")

            if i == 1:  # Introduction
                content_parts.append(f"{topic} {random.choice(intro_sentences)}")
                content_parts.append(random.choice(description_sentences))
            elif i == 2:  # Concepts
                content_parts.append(random.choice(description_sentences))
                content_parts.append("Les aspects clés incluent :")
                for bullet in random.choice(bullet_topics):
                    content_parts.append(f"- {bullet}")
            elif i == 3:  # Applications
                content_parts.append("Les domaines d'application sont nombreux :")
                for bullet in random.choice(bullet_topics):
                    content_parts.append(f"- {bullet}")
            else:  # Challenges
                content_parts.append("Les principaux défis à relever :")
                for bullet in random.choice(challenges):
                    content_parts.append(f"- {bullet}")

            content_parts.append("")  # Empty line between sections

        # Add footer
        content_parts.append(f"Note: Contenu de test généré aléatoirement ({image_count} image(s) détectée(s)).")

        return "\n".join(content_parts)


class MockDraftEnhancer:
    """Mock draft enhancer that returns pre-formatted content without LLM calls."""

    def __init__(self):
        self.state = None

    class State(TypedDict):
        user_input: str
        agent_response: str

    async def structure_content(self, state: "MockDraftEnhancer.State") -> "MockDraftEnhancer.State":
        """Mock structuring - just returns the input with minimal formatting."""
        logger.info("[TEST MODE] Mock structure_content (no LLM call)")
        self.state = state
        state["agent_response"] = state["user_input"]
        return state

    async def enhance_clarity(self, state: "MockDraftEnhancer.State") -> "MockDraftEnhancer.State":
        """Mock enhancement - returns content as-is."""
        logger.info("[TEST MODE] Mock enhance_clarity (no LLM call)")
        state = self.state
        # Keep the content unchanged
        return state

    async def check_facts(self, state: "MockDraftEnhancer.State"):
        """Mock fact checking - always returns 'ok'."""
        logger.info("[TEST MODE] Mock check_facts (no LLM call)")
        return "ok"

    async def out(self, state: "MockDraftEnhancer.State"):
        """Output state."""
        return state

    async def create_notes_workflow(self):
        """Create a mock workflow that bypasses LLM calls."""
        from langgraph.graph import StateGraph

        workflow = StateGraph(self.State)

        # Add nodes with mock implementations
        workflow.add_node("structure", self.structure_content)
        workflow.add_node("enhance", self.enhance_clarity)
        workflow.add_node("out", self.out)

        workflow.add_edge("structure", "enhance")
        workflow.add_conditional_edges(
            "enhance", self.check_facts,
            {
                "ko": "enhance",
                "ok": "out"
            },
        )

        workflow.set_entry_point("structure")

        return workflow.compile()


class MockNotesCreator:
    """Mock notes creator that directly calls Notion API without LLM decision-making."""

    def __init__(self,
                 notion_connector,
                 draft_enhancer,
                 image_text_extractor):
        self.notion_connector = notion_connector
        self.draft_enhancer = draft_enhancer
        self.image_text_extractor = image_text_extractor

    async def notes_creation(self, user_notion_token: str, user_notion_page_id: str):
        """
        Create notes without any LLM calls.

        Args:
            user_notion_token: User's Notion OAuth access token
            user_notion_page_id: User's target Notion page ID
        """
        logger.info("[TEST MODE] MockNotesCreator - No LLM calls for Notion block creation")

        # Get mock content
        query = self.image_text_extractor.extract_text()

        # Process through mock workflow
        workflow = await self.draft_enhancer.create_notes_workflow()
        workflow_result = await workflow.ainvoke({"user_input": query})

        # Connect to Notion MCP server with user's OAuth token
        await self.notion_connector.connect_to_server(user_notion_token)

        # Prepare data with TEST title and timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = f"TEST - {timestamp}"

        if not user_notion_page_id:
            raise ValueError("No Notion page ID provided")

        content = workflow_result["agent_response"]

        logger.info(f"[TEST MODE] Creating Notion page with title: {title}")
        logger.info(f"[TEST MODE] Content length: {len(content)} characters")

        # Create page directly using MCP tools (no LLM decision)
        await self._create_notion_page_directly(title, user_notion_page_id, content)

        logger.info("[TEST MODE] ✅ Page created successfully!")

    async def _create_notion_page_directly(self, title: str, parent_page_id: str, content: str):
        """
        Create Notion blocks directly without LLM deciding the structure.
        This simulates what the LLM would do, but with hardcoded logic.
        """
        # Step 1: Create the page
        logger.info("[TEST MODE] Creating Notion page...")
        try:
            page_result = await self.notion_connector.session.call_tool(
                "API-post-page",
                {
                    "parent": {"page_id": parent_page_id},
                    "properties": {
                        "title": {
                            "title": [{"text": {"content": title}}]
                        }
                    }
                }
            )
        except Exception as e:
            error_str = str(e)
            logger.error(f"[TEST MODE] ❌ Error creating page: {error_str}")
            # Check for specific error patterns (deleted or archived page)
            if ("object_not_found" in error_str.lower() or
                "invalid_request_url" in error_str.lower() or
                "archived" in error_str.lower()):
                raise ValueError("La page Notion configurée n'existe plus ou n'est plus accessible. Veuillez configurer une nouvelle page.")
            # Re-raise the original error if it's not a known pattern
            raise

        # Extract the new page ID from the result
        # Check if the result contains an error
        result_text = "".join([c.text for c in page_result.content])

        if "error" in result_text.lower() and ("object_not_found" in result_text.lower() or
                                                "invalid_request_url" in result_text.lower() or
                                                "archived" in result_text.lower()):
            logger.error(f"[TEST MODE] ❌ Error in page creation result: {result_text[:500]}")
            raise ValueError("La page Notion configurée n'existe plus ou n'est plus accessible. Veuillez configurer une nouvelle page.")

        page_id = self._extract_page_id(page_result)
        if not page_id:
            logger.error(f"[TEST MODE] ❌ Could not extract page ID from result: {result_text[:200]}")
            raise Exception("Échec de la création de la page Notion. Aucun ID de page retourné.")

        logger.info(f"[TEST MODE] Page created with ID: {page_id}")

        # Step 2: Parse content and create blocks
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Determine block type based on content patterns
            if line.startswith('# '):
                # Heading 1
                await self._create_block(page_id, "heading_1", line[2:])
            elif line.startswith('## '):
                # Heading 2
                await self._create_block(page_id, "heading_2", line[3:])
            elif any(line.startswith(f"{i}. ") for i in range(1, 10)):
                # Numbered heading or paragraph
                await self._create_block(page_id, "heading_2", line)
            elif line.startswith('- '):
                # Bulleted list
                await self._create_block(page_id, "bulleted_list_item", line[2:])
            else:
                # Regular paragraph
                await self._create_block(page_id, "paragraph", line)

    async def _create_block(self, page_id: str, block_type: str, text: str):
        """Helper to create a single Notion block."""
        if len(text) > 1500:
            # Split long text into chunks
            chunks = [text[i:i+1500] for i in range(0, len(text), 1500)]
            for chunk in chunks:
                await self._create_single_block(page_id, block_type, chunk)
        else:
            await self._create_single_block(page_id, block_type, text)

    async def _create_single_block(self, page_id: str, block_type: str, text: str):
        """Create a single Notion block via MCP."""
        logger.debug(f"[TEST MODE] Creating {block_type}: {text[:50]}...")

        try:
            await self.notion_connector.session.call_tool(
                "API-patch-block-children",
                {
                    "block_id": page_id,
                    "children": [
                        {
                            "object": "block",
                            "type": block_type,
                            block_type: {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {"content": text}
                                    }
                                ]
                            }
                        }
                    ]
                }
            )
        except Exception as e:
            logger.warning(f"[TEST MODE] ⚠️  Error creating block: {e}")

    def _extract_page_id(self, page_result) -> str:
        """Extract page ID from MCP result."""
        # The result is a CallToolResult with content
        result_text = "".join([c.text for c in page_result.content])

        # Try to parse JSON to extract page ID
        import json
        try:
            result_json = json.loads(result_text)
            return result_json.get("id", "")
        except:
            # Fallback: extract ID from text if JSON parsing fails
            if '"id":' in result_text:
                start = result_text.find('"id":"') + 6
                end = result_text.find('"', start)
                return result_text[start:end]
            return ""
