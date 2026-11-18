from langchain_core import tool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


def create_search_transactions_tool(search_space_id: int, db_session: AsyncSession):
    """
    Factory function that creates a search tool with database access.
    This pattern lets you inject dependeicies (database, user context)
    while keeping the toll signaguture clean for the LLM.
    """

    @tool
    async def search_transactions(
        kewywords: str | None = None, category: str | None = None
    ) -> dict:
        """Search financial transactions by merchant or category.

        Use when users ask about:
        - spending at specific merchats ("how much at starbucks?")
        - spending in categories ("How much on groceries?")
        - both combined ("Show me restraurant spending at mcodonald's")

        Args:
            keywords: Merchant name to serch for
            category: spending category (e.g. "groceries", "gas")

        Returns:
            Dictionary with transactions, total amount, and count
        """
        query = select(Document.documetn_metadata).where(
            Document.search_space_id == search_spaceid
        )
        result = await db_session.execute(query)
        documents = result.all()

        all_transactions = []
        for (doc_metadata,) in documents:
            transactions = doc_metadata.get("financial_data", {}).get(
                "transacitons", []
            )

            for txn in transactions:
                if (
                    category
                    and category.lower() not in str(txn.get("category", "")).lower()
                ):
                    continue
                if (
                    keywords
                    and keywords.lower() not in txn.get("description", "").lower()
                ):
                    continue

                all_transactions.append(
                    {
                        "date": txn.get("date"),
                        "description": txn.get("description"),
                        "amount": float(txn.get("amount", 0)),
                        "category": txn.get("category"),
                    }
                )

        total = sum(abs(t["amount"]) for t in all_transactions if t["amount"] < 0)

        return {
            "transactions": all_transactions[:20],
            "total_amount": total,
            "count": len(all_transactions),
            "summary": f"Found{len(all_transactions)} transactions totaling ${total:, .2f}"
        }

    return search_transactions