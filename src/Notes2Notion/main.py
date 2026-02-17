import asyncio
import argparse
import os
from pathlib import Path

from Notes2Notion.notes_builder import NotesCreator, DraftEnhancer
from Notes2Notion.tooling import ImageTextExtractor, McpNotionConnector
from Notes2Notion.mock_components import (MockImageTextExtractor, MockDraftEnhancer,
                                          MockNotesCreator)

from dotenv import load_dotenv


async def main(test_mode: bool = False):
    """
    Main entry point for Notes2Notion application.

    Args:
        test_mode: If True, uses mock components to avoid LLM calls (for testing).
                   If False, uses real components with LLM calls (production).
    """

    # Get absolute path to notes_pictures directory
    # Path is relative to this file's location
    current_file = Path(__file__)
    notes_pictures_path = current_file.parent / "notes_pictures"
    notes_pictures_path="/Users/alex/PycharmProjects/Notes2Notion/src/Notes2Notion/notes_pictures"

    notion_connexion = McpNotionConnector()

    if test_mode:
        print("\n" + "="*60)
        print("🧪 TEST MODE ENABLED - ZERO LLM calls will be made")
        print("="*60 + "\n")
        image_text_extractor = MockImageTextExtractor(str(notes_pictures_path))
        draft_enhancer = MockDraftEnhancer()
        notes_creator = MockNotesCreator(notion_connexion, draft_enhancer,
                                        image_text_extractor)
    else:
        print("\n" + "="*60)
        print("🚀 PRODUCTION MODE - LLM calls will be made")
        print("="*60 + "\n")
        image_text_extractor = ImageTextExtractor(str(notes_pictures_path))
        draft_enhancer = DraftEnhancer()
        notes_creator = NotesCreator(notion_connexion, draft_enhancer,
                                     image_text_extractor)

    try:
        load_dotenv()
        user_notion_token = os.getenv("NOTION_TOKEN")
        user_notion_page_id = os.getenv("NOTION_PAGE_ID")

        await notes_creator.notes_creation(
            user_notion_token=user_notion_token,
            user_notion_page_id=user_notion_page_id)
        print("\n✅ Notes creation completed successfully!")
    finally:
        await notion_connexion.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert handwritten notes to Notion pages"
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run in test mode (no LLM calls, mock content generation)"
    )

    args = parser.parse_args()
    asyncio.run(main(test_mode=args.test_mode))
