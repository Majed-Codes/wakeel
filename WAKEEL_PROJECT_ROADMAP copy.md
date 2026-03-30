# Wakeel AI - Complete Project Roadmap & Implementation Guide

## 📋 Project Overview

**Wakeel AI** is a voice-first AI financial assistant designed specifically for Saudi SMEs. It understands Saudi dialect, works via WhatsApp, ensures ZATCA compliance, and provides intelligent financial insights.

**Timeline**: 6-9 months (Academic Year 2026)
**Team Size**: 2-4 students recommended
**Budget**: SAR 5,000 - 15,000 (~$1,300 - $4,000)

---

## 🎯 Project Phases

### Phase 1: Foundation & Research (Weeks 1-3)
### Phase 2: MVP Development (Weeks 4-10)
### Phase 3: Testing & Refinement (Weeks 11-16)
### Phase 4: Deployment & Presentation (Weeks 17-20)

---

## 📅 PHASE 1: Foundation & Research (Weeks 1-3)

### Week 1: Market Research & Requirements

**Goals:**
- Validate the problem with real Saudi SME owners
- Define exact features for MVP
- Set up project infrastructure

**Tasks:**
1. **Interview 10-15 Saudi Business Owners**
   - Target: Café owners, small retailers, contractors
   - Questions to ask:
     - How do you currently track finances?
     - What's your biggest accounting pain point?
     - Have you been fined by ZATCA? Why?
     - Would you trust AI with financial data?
   - Document findings in `/research/user-interviews.md`

2. **Competitive Analysis**
   - Research existing solutions: Daftra, Wafeq, Qoyod
   - Identify gaps Wakeel can fill
   - Document in `/research/competitive-analysis.md`

3. **Technical Feasibility Study**
   - Test OpenAI Whisper with Saudi dialect audio samples
   - Test GPT-4 entity extraction from Arabic text
   - Verify ZATCA API documentation availability
   - Test WhatsApp Business API sandbox

**Deliverables:**
- [ ] User interview summary report
- [ ] Competitive analysis document
- [ ] Technical feasibility report
- [ ] Project charter (goals, scope, timeline)

---

### Week 2: Architecture & Design

**Goals:**
- Design system architecture
- Create data models
- Design user flows

**Tasks:**
1. **System Architecture Design**
   - Create architecture diagram showing:
     - WhatsApp/Web interface
     - API Gateway
     - LLM processing pipeline
     - Database structure
     - External integrations (ZATCA, banks)
   - Use tool: draw.io or Excalidraw

2. **Database Design**
   - Design schema for:
     - Users (businesses)
     - Transactions
     - Invoices
     - Zakat calculations
     - Chat history
   - Use: PostgreSQL with TimescaleDB for time-series data

3. **User Flow Mapping**
   - Voice message → transcription → entity extraction → database update
   - ZATCA compliance check flow
   - Loan recommendation flow
   - RAG query flow

**Deliverables:**
- [ ] System architecture diagram
- [ ] Database ER diagram
- [ ] User flow diagrams (minimum 4 core flows)
- [ ] API endpoint documentation (draft)

---

### Week 3: Tech Stack Setup & Proof of Concept

**Goals:**
- Set up development environment
- Create proof of concept for voice processing

**Tasks:**
1. **Development Environment Setup**
   ```bash
   # Initialize project
   mkdir wakeel-ai
   cd wakeel-ai
   
   # Backend
   mkdir backend
   cd backend
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install fastapi uvicorn sqlalchemy psycopg2-binary openai python-dotenv
   
   # Frontend
   cd ..
   npx create-react-app frontend
   cd frontend
   npm install axios framer-motion
   ```

2. **Version Control Setup**
   ```bash
   git init
   git remote add origin [your-github-repo]
   
   # Create .gitignore
   echo "venv/\nnode_modules/\n.env\n__pycache__/" > .gitignore
   ```

3. **Proof of Concept: Voice to Transaction**
   - Record 5 Saudi dialect voice messages
   - Test Whisper API transcription accuracy
   - Test GPT-4 entity extraction
   - Measure accuracy and latency
   - Document results

**Deliverables:**
- [ ] Project repository initialized
- [ ] Development environment documented
- [ ] POC demo video (2-3 minutes)
- [ ] Accuracy metrics report

---

## 🚀 PHASE 2: MVP Development (Weeks 4-10)

### Week 4-5: Core Backend Infrastructure

**Goals:**
- Build API foundation
- Implement authentication
- Set up database

**Tasks:**
1. **API Foundation (FastAPI)**
   ```python
   # /backend/main.py
   from fastapi import FastAPI, HTTPException
   from fastapi.middleware.cors import CORSMiddleware
   
   app = FastAPI(title="Wakeel AI API")
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   
   @app.get("/")
   def read_root():
       return {"message": "Wakeel AI API"}
   ```

2. **Database Models**
   ```python
   # /backend/models.py
   from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
   from sqlalchemy.ext.declarative import declarative_base
   from datetime import datetime
   
   Base = declarative_base()
   
   class Business(Base):
       __tablename__ = "businesses"
       
       id = Column(Integer, primary_key=True)
       name = Column(String)
       phone = Column(String, unique=True)
       email = Column(String)
       created_at = Column(DateTime, default=datetime.utcnow)
   
   class Transaction(Base):
       __tablename__ = "transactions"
       
       id = Column(Integer, primary_key=True)
       business_id = Column(Integer, ForeignKey("businesses.id"))
       amount = Column(Float)
       category = Column(String)
       description = Column(String)
       date = Column(DateTime)
       created_at = Column(DateTime, default=datetime.utcnow)
   ```

3. **Authentication System**
   - Implement JWT-based authentication
   - Use: `python-jose`, `passlib`, `bcrypt`
   - Endpoint: `/auth/register`, `/auth/login`, `/auth/me`

**Deliverables:**
- [ ] FastAPI backend running on localhost
- [ ] Database migrations set up (Alembic)
- [ ] Authentication endpoints working
- [ ] API documentation (auto-generated by FastAPI)

---

### Week 6-7: Voice Processing Pipeline

**Goals:**
- Implement voice transcription
- Build entity extraction
- Create transaction recording

**Tasks:**
1. **Voice Transcription Service**
   ```python
   # /backend/services/transcription.py
   import openai
   from fastapi import UploadFile
   
   class TranscriptionService:
       def __init__(self, api_key: str):
           openai.api_key = api_key
       
       async def transcribe_audio(self, audio_file: UploadFile) -> str:
           """Transcribe audio using OpenAI Whisper"""
           audio_data = await audio_file.read()
           
           response = openai.Audio.transcribe(
               model="whisper-1",
               file=audio_data,
               language="ar"  # Arabic
           )
           
           return response["text"]
   ```

2. **Entity Extraction with LLM**
   ```python
   # /backend/services/extraction.py
   import openai
   import json
   
   class EntityExtractor:
       def __init__(self, api_key: str):
           openai.api_key = api_key
       
       async def extract_transaction(self, text: str) -> dict:
           """Extract transaction details from Arabic text"""
           
           prompt = f"""
           Extract transaction information from this Arabic text:
           "{text}"
           
           Return ONLY valid JSON with these fields:
           {{
               "amount": <number>,
               "vendor": "<string>",
               "category": "<string: OpEx|CapEx|Revenue>",
               "description": "<string>",
               "confidence": <0-1>
           }}
           """
           
           response = openai.ChatCompletion.create(
               model="gpt-4",
               messages=[
                   {"role": "system", "content": "You are a financial data extraction expert for Saudi businesses."},
                   {"role": "user", "content": prompt}
               ],
               temperature=0.1
           )
           
           return json.loads(response.choices[0].message.content)
   ```

3. **Transaction Recording API**
   ```python
   # /backend/routes/transactions.py
   from fastapi import APIRouter, UploadFile, Depends
   
   router = APIRouter(prefix="/transactions", tags=["transactions"])
   
   @router.post("/voice")
   async def create_transaction_from_voice(
       audio: UploadFile,
       business_id: int,
       db: Session = Depends(get_db)
   ):
       # 1. Transcribe
       text = await transcription_service.transcribe_audio(audio)
       
       # 2. Extract entities
       transaction_data = await entity_extractor.extract_transaction(text)
       
       # 3. Validate confidence
       if transaction_data["confidence"] < 0.7:
           return {"status": "needs_confirmation", "data": transaction_data}
       
       # 4. Save to database
       transaction = Transaction(
           business_id=business_id,
           amount=transaction_data["amount"],
           category=transaction_data["category"],
           description=transaction_data["description"]
       )
       db.add(transaction)
       db.commit()
       
       return {"status": "success", "transaction": transaction}
   ```

**Deliverables:**
- [ ] Voice transcription endpoint working
- [ ] Entity extraction with >85% accuracy
- [ ] Transaction recording API functional
- [ ] Unit tests for core functions

---

### Week 8: ZATCA Compliance Module

**Goals:**
- Implement basic ZATCA validation
- Create compliance checking logic

**Tasks:**
1. **ZATCA Invoice Validation**
   ```python
   # /backend/services/zatca.py
   import re
   from datetime import datetime
   
   class ZATCAValidator:
       def __init__(self):
           self.required_fields = [
               "seller_name", "seller_vat", "buyer_name", 
               "date", "total", "vat_amount", "qr_code"
           ]
       
       def validate_invoice(self, invoice_data: dict) -> dict:
           """Validate invoice against ZATCA requirements"""
           
           errors = []
           warnings = []
           
           # Check required fields
           for field in self.required_fields:
               if field not in invoice_data or not invoice_data[field]:
                   errors.append(f"Missing required field: {field}")
           
           # Validate VAT number format
           if "seller_vat" in invoice_data:
               if not self._is_valid_vat(invoice_data["seller_vat"]):
                   errors.append("Invalid VAT number format")
           
           # Check QR code presence (Phase 2 requirement)
           if "qr_code" not in invoice_data:
               errors.append("Missing QR code (ZATCA Phase 2 requirement)")
           
           # VAT calculation check
           if "total" in invoice_data and "vat_amount" in invoice_data:
               expected_vat = invoice_data["total"] * 0.15
               actual_vat = invoice_data["vat_amount"]
               
               if abs(expected_vat - actual_vat) > 0.01:
                   warnings.append(f"VAT calculation mismatch. Expected: {expected_vat}, Got: {actual_vat}")
           
           return {
               "valid": len(errors) == 0,
               "errors": errors,
               "warnings": warnings,
               "compliance_score": self._calculate_score(errors, warnings)
           }
       
       def _is_valid_vat(self, vat_number: str) -> bool:
           """Validate Saudi VAT number format (15 digits)"""
           return bool(re.match(r'^\d{15}$', vat_number))
       
       def _calculate_score(self, errors: list, warnings: list) -> float:
           """Calculate compliance score 0-100"""
           if errors:
               return 0.0
           return max(0, 100 - (len(warnings) * 10))
   ```

2. **Real-time Compliance Monitoring**
   ```python
   @router.post("/validate-invoice")
   async def validate_invoice(invoice_data: dict):
       validator = ZATCAValidator()
       result = validator.validate_invoice(invoice_data)
       
       if not result["valid"]:
           # Trigger alert to user
           await send_alert(
               business_id=invoice_data["business_id"],
               message=f"⚠️ Invoice validation failed: {', '.join(result['errors'])}"
           )
       
       return result
   ```

**Deliverables:**
- [ ] ZATCA validation module
- [ ] Invoice compliance checker
- [ ] Alert system for non-compliant invoices
- [ ] Test cases with sample invoices

---

### Week 9: RAG Implementation (Chat with Data)

**Goals:**
- Implement vector database
- Build RAG query system

**Tasks:**
1. **Vector Database Setup**
   ```bash
   # Install dependencies
   pip install langchain chromadb sentence-transformers
   ```

2. **Document Embedding & Storage**
   ```python
   # /backend/services/rag.py
   from langchain.embeddings import HuggingFaceEmbeddings
   from langchain.vectorstores import Chroma
   from langchain.text_splitter import RecursiveCharacterTextSplitter
   
   class FinancialRAG:
       def __init__(self):
           self.embeddings = HuggingFaceEmbeddings(
               model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
           )
           self.vectorstore = Chroma(
               embedding_function=self.embeddings,
               persist_directory="./chroma_db"
           )
       
       def index_transactions(self, transactions: list):
           """Index transactions for RAG queries"""
           
           # Convert transactions to text documents
           documents = []
           for t in transactions:
               doc_text = f"""
               التاريخ: {t.date}
               المبلغ: {t.amount} ريال
               الفئة: {t.category}
               الوصف: {t.description}
               المورد: {t.vendor if hasattr(t, 'vendor') else 'غير محدد'}
               """
               documents.append(doc_text)
           
           # Split and embed
           text_splitter = RecursiveCharacterTextSplitter(
               chunk_size=500,
               chunk_overlap=50
           )
           chunks = text_splitter.create_documents(documents)
           
           # Store in vector DB
           self.vectorstore.add_documents(chunks)
   ```

3. **Query Answering**
   ```python
   async def answer_query(self, query: str, business_id: int) -> str:
       """Answer questions about financial data"""
       
       # Retrieve relevant context
       relevant_docs = self.vectorstore.similarity_search(
           query, 
           k=5,
           filter={"business_id": business_id}
       )
       
       context = "\n\n".join([doc.page_content for doc in relevant_docs])
       
       # Generate answer with GPT-4
       prompt = f"""
       Based on this financial data:
       {context}
       
       Answer this question in Arabic: {query}
       
       Provide specific numbers and dates. Be concise.
       """
       
       response = openai.ChatCompletion.create(
           model="gpt-4",
           messages=[
               {"role": "system", "content": "You are Wakeel, a financial assistant for Saudi businesses."},
               {"role": "user", "content": prompt}
           ]
       )
       
       return response.choices[0].message.content
   ```

**Deliverables:**
- [ ] Vector database set up and indexed
- [ ] RAG query endpoint functional
- [ ] Test queries with sample data
- [ ] Response accuracy >80%

---

### Week 10: Frontend Development

**Goals:**
- Build core UI components
- Connect frontend to backend
- Create chat interface

**Tasks:**
1. **Chat Interface Component**
   ```jsx
   // /frontend/src/components/ChatInterface.jsx
   import React, { useState } from 'react';
   import axios from 'axios';
   
   const ChatInterface = () => {
     const [messages, setMessages] = useState([]);
     const [recording, setRecording] = useState(false);
     
     const handleVoiceMessage = async (audioBlob) => {
       const formData = new FormData();
       formData.append('audio', audioBlob);
       
       try {
         const response = await axios.post(
           'http://localhost:8000/transactions/voice',
           formData,
           {
             headers: { 'Content-Type': 'multipart/form-data' }
           }
         );
         
         setMessages([...messages, {
           type: 'assistant',
           content: `تم التسجيل: ${response.data.transaction.amount} ريال`
         }]);
       } catch (error) {
         console.error('Error:', error);
       }
     };
     
     return (
       <div className="chat-container">
         {/* Chat messages */}
         {/* Voice recording button */}
         {/* Text input */}
       </div>
     );
   };
   ```

2. **Dashboard Components**
   - Financial overview cards
   - Transaction history table
   - Charts (use Recharts or Chart.js)
   - ZATCA compliance status

3. **API Integration**
   ```javascript
   // /frontend/src/services/api.js
   import axios from 'axios';
   
   const API_BASE = 'http://localhost:8000';
   
   export const api = {
     // Transactions
     getTransactions: () => axios.get(`${API_BASE}/transactions`),
     createVoiceTransaction: (audio) => {
       const formData = new FormData();
       formData.append('audio', audio);
       return axios.post(`${API_BASE}/transactions/voice`, formData);
     },
     
     // Chat
     sendMessage: (message) => axios.post(`${API_BASE}/chat`, { message }),
     
     // Auth
     login: (credentials) => axios.post(`${API_BASE}/auth/login`, credentials)
   };
   ```

**Deliverables:**
- [ ] Functional chat interface
- [ ] Dashboard showing financial data
- [ ] Voice recording capability
- [ ] Frontend-backend integration complete

---

## 🧪 PHASE 3: Testing & Refinement (Weeks 11-16)

### Week 11-12: Beta Testing with Real Users

**Goals:**
- Test with 5-10 Saudi business owners
- Collect feedback
- Measure accuracy

**Tasks:**
1. **Recruit Beta Testers**
   - Target: Small café owners, retail shops
   - Offer: Free usage for 2 months
   - Collect: Phone numbers for WhatsApp testing

2. **Beta Testing Plan**
   ```markdown
   ## Beta Test Scenarios
   
   ### Scenario 1: Daily Transactions
   - Record 20 voice messages over 2 weeks
   - Track: Accuracy, response time, user satisfaction
   
   ### Scenario 2: Invoice Validation
   - Upload 10 invoices
   - Check: ZATCA compliance detection
   
   ### Scenario 3: Financial Queries
   - Ask 15 different questions
   - Measure: Answer accuracy, relevance
   ```

3. **Data Collection**
   - User satisfaction surveys
   - Accuracy logs (transcription, extraction)
   - Error reports
   - Feature requests

**Deliverables:**
- [ ] Beta testing report
- [ ] Bug list prioritized
- [ ] Feature improvement list
- [ ] Accuracy metrics report

---

### Week 13-14: Bug Fixes & Improvements

**Goals:**
- Fix critical bugs
- Improve accuracy
- Enhance UX based on feedback

**Priority Bug Fixes:**
1. Voice transcription errors (Saudi dialect)
2. Entity extraction misses
3. UI/UX issues
4. Performance bottlenecks

**Improvements:**
1. **Confidence Threshold Adjustment**
   - If extraction confidence < 0.8, ask for confirmation
   - Show extracted data to user before saving

2. **Error Handling**
   ```python
   try:
       transaction = await create_transaction(data)
   except ValueError as e:
       return {
           "status": "error",
           "message": "لم أتمكن من فهم المبلغ. هل يمكنك إعادة المحاولة؟",
           "suggestion": "مثال: حولت خمسة آلاف ريال للمورد"
       }
   ```

3. **Performance Optimization**
   - Add caching for frequent queries
   - Optimize database queries
   - Implement background jobs for heavy tasks

**Deliverables:**
- [ ] All critical bugs fixed
- [ ] Accuracy improved to >90%
- [ ] Performance improved (response time <3s)
- [ ] Updated documentation

---

### Week 15-16: WhatsApp Integration

**Goals:**
- Connect to WhatsApp Business API
- Enable real WhatsApp conversations

**Tasks:**
1. **WhatsApp Business API Setup**
   ```bash
   # Option 1: Use Twilio
   pip install twilio
   
   # Option 2: Use official WhatsApp Business API
   # Requires: Facebook Business Manager account
   ```

2. **Webhook Handler**
   ```python
   # /backend/routes/whatsapp.py
   from fastapi import APIRouter, Request
   from twilio.rest import Client
   
   router = APIRouter(prefix="/whatsapp")
   
   @router.post("/webhook")
   async def whatsapp_webhook(request: Request):
       data = await request.form()
       
       incoming_msg = data.get('Body', '')
       from_number = data.get('From', '')
       
       # Check if it's a voice message
       if data.get('MediaContentType0', '').startswith('audio/'):
           audio_url = data.get('MediaUrl0')
           # Process voice message
           response = await process_voice_message(audio_url, from_number)
       else:
           # Process text message
           response = await process_text_message(incoming_msg, from_number)
       
       # Send response back
       send_whatsapp_message(from_number, response)
       
       return {"status": "ok"}
   ```

3. **Testing**
   - Test with real WhatsApp account
   - Verify voice message handling
   - Test message delivery

**Deliverables:**
- [ ] WhatsApp integration working
- [ ] Voice messages processed correctly
- [ ] Two-way conversation functional
- [ ] Test documentation

---

## 🚢 PHASE 4: Deployment & Presentation (Weeks 17-20)

### Week 17: Deployment Setup

**Goals:**
- Deploy to cloud
- Set up production environment

**Tasks:**
1. **Cloud Deployment (AWS/DigitalOcean)**
   ```bash
   # Backend deployment with Docker
   # Dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Database Migration to Production**
   - Use: AWS RDS PostgreSQL or DigitalOcean Managed Database
   - Run migrations: `alembic upgrade head`

3. **Frontend Deployment**
   - Deploy to: Vercel or Netlify
   - Connect to production API

4. **Domain & SSL**
   - Register: wakeel.ai (or similar)
   - Set up SSL certificate
   - Configure DNS

**Deliverables:**
- [ ] Backend deployed and accessible
- [ ] Frontend deployed with custom domain
- [ ] Database production-ready
- [ ] Monitoring set up (basic)

---

### Week 18: Documentation & Video Demo

**Goals:**
- Create comprehensive documentation
- Record demo video
- Prepare presentation

**Tasks:**
1. **Technical Documentation**
   - System architecture
   - API documentation
   - Database schema
   - Deployment guide
   - User manual

2. **Demo Video (5-7 minutes)**
   Script outline:
   ```markdown
   ## Demo Video Script
   
   [0:00-0:30] Problem Statement
   - Show struggling SME owner with receipts
   - Mention ZATCA fines statistics
   
   [0:30-1:00] Solution Introduction
   - Introduce Wakeel AI
   - Show logo and tagline
   
   [1:00-3:00] Feature Demonstrations
   1. Voice transaction recording (Saudi dialect)
   2. ZATCA compliance check
   3. Financial query with RAG
   4. WhatsApp conversation
   
   [3:00-4:00] Technical Architecture
   - Show system diagram
   - Explain key technologies
   
   [4:00-5:00] Results & Impact
   - Beta testing results
   - Accuracy metrics
   - User testimonials
   
   [5:00-7:00] Future Vision
   - Loan hunting feature
   - Regional expansion
   - Open Banking integration
   ```

3. **Academic Presentation (20-30 slides)**
   - Problem & motivation
   - Literature review
   - System design
   - Implementation details
   - Testing & results
   - Conclusion & future work

**Deliverables:**
- [ ] Complete technical documentation
- [ ] Professional demo video
- [ ] Presentation slides
- [ ] User manual (Arabic & English)

---

### Week 19: Final Testing & Polish

**Goals:**
- End-to-end testing
- Fix any remaining issues
- Polish UI/UX

**Critical Tests:**
1. **End-to-End User Journey**
   - Sign up → Record transaction → View dashboard → Ask question
   - Measure: Time to complete, errors encountered

2. **Load Testing**
   - Simulate 50 concurrent users
   - Ensure response time < 3 seconds

3. **Security Testing**
   - Check authentication
   - Test SQL injection protection
   - Verify API rate limiting

4. **Accessibility Testing**
   - Test with screen readers
   - Check color contrast
   - Verify keyboard navigation

**Deliverables:**
- [ ] All tests passing
- [ ] Security audit complete
- [ ] Performance benchmarks documented
- [ ] Final bug fixes deployed

---

### Week 20: Presentation & Defense

**Goals:**
- Present to faculty
- Defend technical decisions
- Demonstrate live system

**Presentation Structure:**
1. **Introduction (3 minutes)**
   - Problem statement
   - Market need in Saudi Arabia
   - Vision 2030 alignment

2. **Technical Design (5 minutes)**
   - Architecture overview
   - Key technologies chosen (and why)
   - Challenges overcome

3. **Live Demonstration (7 minutes)**
   - Voice transaction recording
   - ZATCA validation
   - Financial query
   - WhatsApp conversation

4. **Results & Validation (3 minutes)**
   - Accuracy metrics
   - Beta testing feedback
   - Performance benchmarks

5. **Conclusion & Future Work (2 minutes)**
   - Achievements
   - Limitations
   - Future enhancements
   - Commercial potential

**Q&A Preparation:**
Common questions:
- Why not use existing accounting software?
- How do you handle data privacy?
- What if the AI makes a mistake?
- How scalable is the system?
- What's the cost to run this?

**Deliverables:**
- [ ] Final presentation delivered
- [ ] Live demo successful
- [ ] Questions answered satisfactorily
- [ ] Project approved

---

## 💰 Budget Breakdown

### Minimum Budget: SAR 5,000 (~$1,300)

| Item | Cost (SAR) | Notes |
|------|-----------|-------|
| OpenAI API Credits | 1,500 | GPT-4 + Whisper (~3 months testing) |
| Cloud Hosting | 1,200 | DigitalOcean Droplet ($40/month × 3) |
| WhatsApp Business API | 800 | Twilio credits for testing |
| Domain & SSL | 200 | wakeel.sa domain |
| Testing Devices | 500 | Used Android phone for testing |
| Contingency | 800 | Unexpected costs |
| **Total** | **5,000** | |

### Recommended Budget: SAR 15,000 (~$4,000)

| Item | Cost (SAR) | Notes |
|------|-----------|-------|
| OpenAI API Credits | 4,000 | More extensive testing |
| Cloud Hosting | 2,400 | Better infrastructure (6 months) |
| WhatsApp Business API | 2,000 | Official Meta Business API |
| Database (Managed) | 1,800 | AWS RDS PostgreSQL |
| Domain & Branding | 800 | Domain + logo design |
| User Testing Incentives | 2,000 | Pay beta testers |
| Marketing Materials | 1,000 | Video production, website |
| Contingency | 1,000 | Buffer |
| **Total** | **15,000** | |

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15 with TimescaleDB
- **Vector DB**: ChromaDB or Pinecone
- **Authentication**: JWT with python-jose
- **Task Queue**: Celery with Redis (optional)

### AI/ML
- **LLM**: OpenAI GPT-4 Turbo
- **Speech-to-Text**: OpenAI Whisper
- **Embeddings**: sentence-transformers (multilingual model)
- **RAG Framework**: LangChain

### Frontend
- **Framework**: React 18 with TypeScript
- **UI Library**: Tailwind CSS
- **Animations**: Framer Motion
- **State Management**: React Context / Zustand
- **Charts**: Recharts

### Integration
- **WhatsApp**: Twilio API or Meta Business API
- **ZATCA**: REST API (when available) or rule-based validation

### DevOps
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Hosting**: DigitalOcean / AWS EC2
- **Monitoring**: Sentry (errors) + Uptime Robot

---

## 📚 Required Skills & Learning Resources

### Must-Have Skills
1. **Python Backend Development**
   - FastAPI tutorial: https://fastapi.tiangolo.com/tutorial/
   - SQLAlchemy ORM: https://docs.sqlalchemy.org/

2. **React Frontend Development**
   - React docs: https://react.dev/
   - TypeScript: https://www.typescriptlang.org/docs/

3. **AI/ML Integration**
   - OpenAI API: https://platform.openai.com/docs
   - LangChain: https://python.langchain.com/docs/

4. **Database Design**
   - PostgreSQL: https://www.postgresql.org/docs/
   - Database normalization principles

### Nice-to-Have Skills
1. Docker & deployment
2. Arabic NLP understanding
3. UI/UX design principles
4. Cloud infrastructure (AWS/Azure)

### Learning Timeline
- **Weeks 1-2**: FastAPI + React fundamentals
- **Weeks 3-4**: OpenAI API + LangChain
- **Weeks 5-6**: Database design + SQLAlchemy
- **Ongoing**: Arabic language processing nuances

---

## 🎯 Success Metrics

### Academic Success
- [ ] All project milestones completed on time
- [ ] Working demo with >90% uptime
- [ ] Comprehensive documentation
- [ ] Successful presentation defense
- [ ] Grade: A or equivalent

### Technical Success
- [ ] Voice transcription accuracy >95% (Saudi dialect)
- [ ] Entity extraction accuracy >90%
- [ ] API response time <3 seconds
- [ ] Zero critical security vulnerabilities
- [ ] >85% test coverage

### User Success (Beta Testing)
- [ ] 10+ active beta users
- [ ] User satisfaction score >4/5
- [ ] 50+ successful voice transactions
- [ ] 5+ ZATCA violations prevented
- [ ] Positive testimonials collected

### Commercial Potential
- [ ] 100+ waitlist signups
- [ ] Interest from 1-2 potential investors
- [ ] Media coverage (local tech blog)
- [ ] Clear path to monetization defined

---

## 🚨 Risk Management

### High Risks

**Risk 1: Voice Recognition Accuracy Issues**
- **Probability**: High
- **Impact**: Critical
- **Mitigation**: 
  - Start testing with Whisper API immediately
  - Collect diverse Saudi dialect samples
  - Implement confidence scoring
  - Add manual correction option

**Risk 2: ZATCA API Access**
- **Probability**: Medium
- **Impact**: High
- **Mitigation**:
  - Build rule-based validation first
  - Contact ZATCA for developer access
  - Use documented requirements as fallback
  - Make it a "future integration" if needed

**Risk 3: WhatsApp API Restrictions**
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**:
  - Start with Twilio sandbox
  - Have web interface as alternative
  - Apply for official access early
  - Document web version as primary, WhatsApp as bonus

### Medium Risks

**Risk 4: Scope Creep**
- **Probability**: High
- **Impact**: Medium
- **Mitigation**:
  - Define strict MVP features
  - Use "Future Work" slide for extras
  - Weekly progress reviews
  - Prioritization matrix

**Risk 5: Team Member Dropout**
- **Probability**: Medium
- **Impact**: High
- **Mitigation**:
  - Clear role assignments
  - Weekly check-ins
  - Document everything
  - Modular architecture (one person can continue)

---

## 📞 Next Steps (Starting Today)

### This Week
1. **Day 1-2**: Read this entire roadmap
2. **Day 3**: Set up GitHub repository
3. **Day 4-5**: Install development environment
4. **Day 6-7**: Complete Week 1 user interviews

### This Month
1. Complete Phase 1 (Foundation & Research)
2. Set up backend and frontend skeleton
3. Test OpenAI APIs with Saudi dialect samples
4. Create first working prototype (voice → text → database)

### This Quarter
1. Complete MVP (Phase 2)
2. Start beta testing
3. Prepare demo video
4. Build waitlist landing page

---

## 🤝 Team Roles (Recommended for 4-person team)

**Person 1: Backend Lead**
- API development
- Database design
- AI/ML integration
- Security & authentication

**Person 2: Frontend Lead**
- React development
- UI/UX implementation
- Mobile responsiveness
- User testing coordination

**Person 3: AI/ML Specialist**
- Voice processing pipeline
- Entity extraction optimization
- RAG implementation
- Accuracy improvement

**Person 4: Integration & DevOps**
- WhatsApp integration
- ZATCA compliance module
- Deployment & hosting
- Documentation & testing

*For 2-person team: Combine roles (Backend+AI and Frontend+DevOps)*

---

## 📖 Additional Resources

### Documentation Templates
- API documentation: Use FastAPI auto-generated docs
- User manual: Create in Notion or GitBook
- Technical report: IEEE paper template

### Code Repositories to Study
- LangChain examples: https://github.com/langchain-ai/langchain
- FastAPI projects: https://github.com/topics/fastapi
- React dashboards: https://github.com/topics/react-dashboard

### Saudi-Specific Resources
- ZATCA e-invoicing: https://zatca.gov.sa/en/eInvoicing/
- Saudi Open Banking: https://openbanking.sa/
- Vision 2030 SME support: https://www.vision2030.gov.sa/

---

## 🎉 Conclusion

Wakeel AI is an ambitious but achievable project that addresses a real problem in the Saudi market. With this roadmap:

✅ You have a clear path from concept to deployment
✅ You understand the technical requirements
✅ You know exactly what to build and when
✅ You have risk mitigation strategies
✅ You're aligned with academic requirements

**Remember**: 
- Start small, iterate quickly
- Test with real users early
- Don't chase perfection—chase working software
- Document everything as you go
- Celebrate small wins along the way

**Good luck building Wakeel AI! 🚀**

---

*Last Updated: February 2026*
*Version: 1.0*
*Prepared for: Academic Senior Project*