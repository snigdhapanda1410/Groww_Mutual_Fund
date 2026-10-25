"""Centralized configuration management using Pydantic Settings."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable fallback."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Inference (Groq)
    groq_api_key: str = Field(
        default="",
        description="API key for Groq Cloud API",
    )
    groq_model: str = Field(
        default="openai/gpt-oss-120b",
        description="Groq model name",
    )
    llm_temperature: float = Field(
        default=0.0,
        description="LLM temperature for deterministic factual generation",
    )
    llm_top_p: float = Field(
        default=0.1,
        description="LLM top_p sampling",
    )
    llm_max_output_tokens: int = Field(
        default=600,
        description="Maximum tokens generated per response (including reasoning tokens)",
    )
    llm_rpm_limit: int = Field(
        default=30,
        description="Rate limit: requests per minute",
    )
    llm_rpd_limit: int = Field(
        default=1000,
        description="Rate limit: requests per day",
    )
    llm_tpm_limit: int = Field(
        default=8000,
        description="Rate limit: tokens per minute",
    )
    llm_tpd_limit: int = Field(
        default=200000,
        description="Rate limit: tokens per day",
    )

    # Vector Storage (ChromaDB)
    chroma_persist_directory: str = Field(
        default="./data/chromadb",
        description="Directory for ChromaDB persistent database",
    )
    chroma_collection_name: str = Field(
        default="hdfc_mutual_fund_facts",
        description="Name of the ChromaDB collection",
    )
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="SentenceTransformers local embedding model name",
    )
    retrieval_top_k: int = Field(
        default=3,
        description="Number of context chunks to retrieve",
    )
    similarity_threshold: float = Field(
        default=0.65,
        description="Cosine distance rejection threshold",
    )
    use_reranker: bool = Field(
        default=False,
        description="Enable secondary reranking on retrieved chunks",
    )

    # Output Contract Enforcement
    max_output_sentences: int = Field(
        default=3,
        description="Strict ceiling on sentence count for facts-only answers",
    )
    enforce_single_citation: bool = Field(
        default=True,
        description="Guarantee exactly one authoritative citation URL",
    )

    # Application & Regulatory Compliance
    sebi_disclaimer_text: str = Field(
        default="Facts-only. No investment advice.",
        description="SEBI regulatory disclaimer banner text",
    )
    app_title: str = Field(
        default="Groww | Mutual Fund FAQ Assistant",
        description="Application title displayed in UI",
    )
    session_persist_path: str = Field(
        default="./data/sessions/",
        description="Directory for local session JSON persistence",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )


# Global configuration instance
config = Settings()
