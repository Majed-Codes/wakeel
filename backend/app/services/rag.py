"""
RAG Service — Chat with your financial data.

Uses ChromaDB for vector retrieval + Anthropic Claude for generation.
Falls back to OpenAI GPT-4o if Anthropic key is not available.
Supports conversation history for context-aware responses.
"""

import logging
from typing import List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """أنت "وكيل"، المساعد المالي الذكي للمنشآت الصغيرة والمتوسطة في السعودية.

شخصيتك:
- تتحدث بالعربية الفصحى مع لمسة سعودية ودية
- تفهم المصطلحات المالية السعودية (زكاة، ضريبة القيمة المضافة، فاتورة إلكترونية، ZATCA)
- تعطي إجابات مختصرة ودقيقة مع أرقام محددة عند توفرها
- تنصح بشكل عملي وتوجه لتحسين الأداء المالي

قدراتك:
- تحليل المعاملات المالية (مصاريف، إيرادات، أرباح)
- الإجابة عن أسئلة حول المصاريف والإيرادات
- تقديم نصائح مالية بسيطة
- المساعدة في فهم متطلبات الامتثال الضريبي (ZATCA)

قواعد:
- إذا لم تتوفر بيانات كافية، أخبر المستخدم بوضوح
- استخدم الأرقام والتواريخ من البيانات المتوفرة
- لا تختلق أرقام أو بيانات غير موجودة
- إذا سألك المستخدم سؤال خارج نطاقك المالي، وجهه بلطف"""


class FinancialRAG:
    """خدمة المحادثة الذكية مع البيانات المالية"""

    def __init__(self):
        self._client = None
        self._openai_client = None
        self._vectorstore = None

        if settings.has_anthropic_key:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            logger.info("RAG chat: using Anthropic Claude")
        elif settings.has_openai_key:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("RAG chat: using OpenAI GPT-4o (fallback)")

        # ChromaDB initialization (lazy — only when needed)
        self._initialized = False

    def _init_vectorstore(self):
        """Lazy-init ChromaDB. Only called when first query comes in."""
        if self._initialized:
            return

        try:
            import chromadb
            self._chroma_client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR
            )
            self._collection = self._chroma_client.get_or_create_collection(
                name="wakeel_transactions",
                metadata={"hnsw:space": "cosine"},
            )
            self._initialized = True
            logger.info("ChromaDB initialized successfully")
        except Exception as e:
            logger.warning(f"ChromaDB init failed (not critical for MVP): {e}")
            self._initialized = False

    def index_transactions(self, transactions: list, business_id: int):
        """Index transactions into vector DB for RAG queries."""
        self._init_vectorstore()
        if not self._initialized:
            return

        documents = []
        ids = []
        metadatas = []

        for t in transactions:
            doc_text = (
                f"معاملة رقم {t.id} | التاريخ: {t.date} | "
                f"المبلغ: {t.amount:,.2f} ريال | "
                f"الفئة: {t.category or 'غير مصنف'} | "
                f"الوصف: {t.description or 'بدون وصف'} | "
                f"المورد: {t.vendor or 'غير محدد'} | "
                f"المصدر: {t.source}"
            )
            documents.append(doc_text)
            ids.append(f"txn_{t.id}")
            metadatas.append({"business_id": str(business_id)})

        if documents:
            self._collection.upsert(
                documents=documents,
                ids=ids,
                metadatas=metadatas,
            )
            logger.info(f"Indexed {len(documents)} transactions for business {business_id}")

    def index_single_transaction(self, transaction, business_id: int):
        """Index a single transaction into vector DB."""
        self._init_vectorstore()
        if not self._initialized:
            return

        doc_text = (
            f"معاملة رقم {transaction.id} | التاريخ: {transaction.date} | "
            f"المبلغ: {transaction.amount:,.2f} ريال | "
            f"الفئة: {transaction.category or 'غير مصنف'} | "
            f"الوصف: {transaction.description or 'بدون وصف'} | "
            f"المورد: {transaction.vendor or 'غير محدد'} | "
            f"المصدر: {transaction.source}"
        )

        try:
            self._collection.upsert(
                documents=[doc_text],
                ids=[f"txn_{transaction.id}"],
                metadatas=[{"business_id": str(business_id)}],
            )
        except Exception as e:
            logger.warning(f"Failed to index transaction {transaction.id}: {e}")

    async def answer_query(
        self,
        query: str,
        business_id: int,
        chat_history: Optional[List[dict]] = None,
    ) -> str:
        """
        Answer a financial question using RAG.

        1. Retrieve relevant transactions from vector DB
        2. Build conversation context from chat history
        3. Pass everything to Claude (or GPT-4o fallback)
        4. Return the answer in Arabic
        """
        if not self._client and not self._openai_client:
            return self._mock_answer(query)

        # Fallback to OpenAI if Anthropic not available
        if not self._client and self._openai_client:
            return await self._answer_openai(query, business_id, chat_history)

        # Retrieve relevant context from vector DB
        context = self._retrieve_context(query, business_id)

        # Build messages array (Anthropic requires alternating user/assistant)
        messages = []

        if chat_history:
            for msg in chat_history[-10:]:  # last 10 messages (5 exchanges)
                role = msg["role"]
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": msg["content"]})

        # Add the current query with retrieved context
        user_message = f"""البيانات المالية المتوفرة:
{context}

سؤال المستخدم: {query}"""

        messages.append({"role": "user", "content": user_message})

        # Ensure messages start with "user" role (Anthropic requirement)
        while messages and messages[0]["role"] != "user":
            messages.pop(0)

        # Merge consecutive same-role messages (Anthropic requirement)
        merged = []
        for msg in messages:
            if merged and merged[-1]["role"] == msg["role"]:
                merged[-1]["content"] += "\n" + msg["content"]
            else:
                merged.append(msg)
        messages = merged

        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-20250514",
                system=SYSTEM_PROMPT,
                messages=messages,
                temperature=0.3,
                max_tokens=600,
            )
            return response.content[0].text
        except Exception as e:
            error_str = str(e)
            logger.error(f"RAG query failed: {error_str}")
            if "overloaded" in error_str.lower():
                return (
                    "عذراً، خدمة الذكاء الاصطناعي مشغولة حالياً. "
                    "يرجى المحاولة بعد لحظات."
                )
            if "rate_limit" in error_str.lower():
                return "عذراً، الخدمة مشغولة حالياً. يرجى المحاولة بعد لحظات."
            return "عذراً، حدث خطأ في معالجة سؤالك. يرجى المحاولة مرة أخرى."

    async def _answer_openai(
        self,
        query: str,
        business_id: int,
        chat_history: Optional[List[dict]] = None,
    ) -> str:
        """Fallback: answer using OpenAI GPT-4o if Anthropic is unavailable."""
        context = self._retrieve_context(query, business_id)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if chat_history:
            for msg in chat_history[-10:]:
                messages.append({"role": msg["role"], "content": msg["content"]})

        user_message = f"""البيانات المالية المتوفرة:
{context}

سؤال المستخدم: {query}"""

        messages.append({"role": "user", "content": user_message})

        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.3,
                max_tokens=600,
            )
            return response.choices[0].message.content
        except Exception as e:
            error_str = str(e)
            logger.error(f"OpenAI RAG query failed: {error_str}")
            if "insufficient_quota" in error_str or "quota" in error_str:
                return (
                    "عذراً، رصيد خدمة الذكاء الاصطناعي منتهي. "
                    "يرجى تجديد اشتراك OpenAI API أو التواصل مع الدعم الفني."
                )
            if "429" in error_str or "rate_limit" in error_str:
                return "عذراً، الخدمة مشغولة حالياً. يرجى المحاولة بعد لحظات."
            return "عذراً، حدث خطأ في معالجة سؤالك. يرجى المحاولة مرة أخرى."

    def _retrieve_context(self, query: str, business_id: int) -> str:
        """Retrieve relevant documents from vector DB."""
        self._init_vectorstore()
        if not self._initialized:
            return "لا توجد بيانات مفهرسة حالياً."

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=10,
                where={"business_id": str(business_id)},
            )
            if results and results["documents"] and results["documents"][0]:
                docs = results["documents"][0]
                return "\n".join(f"• {doc}" for doc in docs)
        except Exception as e:
            logger.warning(f"Vector search failed: {e}")

        return "لا توجد بيانات مطابقة."

    def _mock_answer(self, query: str) -> str:
        """Mock answer for development without API key."""
        return (
            "مرحباً! أنا وكيل، مساعدك المالي. "
            "حالياً أعمل في وضع التطوير بدون مفتاح API. "
            f"سؤالك كان: '{query}'. "
            "عند تفعيل المفتاح، سأتمكن من تحليل بياناتك المالية والإجابة بدقة."
        )


financial_rag = FinancialRAG()
