# CommandIA

**CommandIA** is a Darija/Franco-Arabic conversational AI assistant that automates Instagram/Facebook sales, captures orders, and extracts structured data for Algerian e-commerce businesses.

## One-line summary

A Darija/Franco-Arabic conversational AI assistant that automates Instagram/Facebook sales, captures orders, and extracts structured data for Algerian e-commerce businesses.

## About

E-commerce in Algeria relies heavily on social media platforms (Instagram & Facebook Messenger). Local store holders spend hours every day manually answering repetitive inquiries ("Prix svp?", "Bchhal livraison l Sétif?") and manually copying customer details into spreadsheets. Standard Western chatbots fail because they cannot process mixed Algerian Franco-Arabic, Latin-script Darija, or localized delivery formats.

CommandIA acts as an intelligent conversational engine connected directly to the Meta APIs (Instagram/Messenger). It communicates naturally in Franco-Arabic/Darija, answers pricing and product questions, guides customers through the buying process, and extracts structured order details (Name, Phone, Wilaya, Commune) directly into a merchant dashboard. By automating the order-taking process, CommandIA reduces manual labor and minimizes COD return rates caused by inaccurate delivery data.

## Run locally

- Backend (FastAPI): `uvicorn backend.app:app --port 8000`
- Frontend (React + TypeScript + Vite): `npm install && npm run dev` (in `frontend/`)
- AI layer: `ai/`
- Tests: `pytest -q`

Demo helpers:

- Interactive demo: `python -m backend.demo`
- Scripted AI check: `python -m backend.test_ai`
- Signed Instagram webhook emulator: `python -m backend.emulator`

## Tech stack

FastAPI, Python, Supabase (PostgreSQL), Pydantic, Meta Graph API, Ngrok, Figma, Gemini, Git.

## Team

- **Fadoua Cheriet** — Designed the Supabase relational database schema and built the FastAPI webhook infrastructure.
- **Naila Lamia Betouche** — Designed the brand identity and the interactive Figma merchant dashboard.
- **Sebih Abderrahman Oussama** — Developed the LLM prompt engineering and Pydantic data extraction pipeline.
