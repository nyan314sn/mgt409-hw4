"""Pydantic / PydanticAI structured types shared by the API, the agent, and its tools.

API models serialize to camelCase (e.g. garmentType, productId) to match the React app.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---------- catalogue ----------

class SizeStock(CamelModel):
    size: str
    quantity: int


class Product(CamelModel):
    """A full product, as shown on the Products and product-detail pages."""
    id: str
    name: str
    garment_type: str
    category: str
    description: str
    colors: list[str]
    tags: list[str]
    image: str = Field(description="URL path of the product photo, e.g. /data/products/x.jpg")
    price: float
    sizes: list[SizeStock]


class ProductSummary(BaseModel):
    """Compact search result handed to the agent (keeps tool output short)."""
    id: str
    name: str
    category: str
    price: float
    colors: list[str]
    sizes_in_stock: list[str]
    description: str


# ---------- tool lookup results (returned to the agent) ----------

StockStatus = Literal["in_stock", "low_stock", "sold_out"]


class ProductRef(BaseModel):
    """Just enough to name a product and look it up again."""
    id: str
    name: str


class ProductMatch(BaseModel):
    """How a shopper's wording was matched to a catalogue product."""
    query: str = Field(description="What the shopper (or agent) asked for.")
    match_type: Literal["exact_id", "exact_name", "partial", "fuzzy"]
    note: str | None = Field(
        default=None,
        description="Set for fuzzy matches, e.g. \"'saybrok crewnek' matched 'Saybrook College Crewneck'\". "
                    "Confirm the product name with the shopper when present.",
    )


class LookupMiss(BaseModel):
    """Returned instead of a result when the product can't be pinned down. Never guess."""
    query: str
    reason: Literal["not_found", "ambiguous"]
    message: str
    suggestions: list[ProductRef] = Field(default_factory=list, description="Closest real products, best first.")


class PriceInfo(BaseModel):
    product: ProductRef
    match: ProductMatch
    price: float = Field(description="Price in US dollars, straight from the catalogue table.")
    currency: Literal["USD"] = "USD"


class DescriptionInfo(BaseModel):
    product: ProductRef
    match: ProductMatch
    category: str
    garment_type: str
    description: str
    colors: list[str]


class SizeStockStatus(BaseModel):
    size: str
    quantity: int = Field(description="Units on hand from the inventory table.")
    status: StockStatus = Field(description="sold_out = 0 units; low_stock = 1-4 units; in_stock = 5+.")


class StockReport(BaseModel):
    product: ProductRef
    match: ProductMatch
    requested_size: str | None = Field(
        default=None, description="Normalized size the shopper asked about (e.g. 'medium' -> 'M'), if any.")
    requested_size_status: StockStatus | Literal["size_not_offered"] | None = None
    requested_size_quantity: int | None = None
    sizes: list[SizeStockStatus] = Field(description="Every size, XS to XXL, in order.")
    available_sizes: list[str]
    sold_out_sizes: list[str]
    total_in_stock: int


# ---------- agent output ----------

MAX_SHOWCASE = 12


class AgentReply(BaseModel):
    """What the shop agent returns each turn (its structured output).

    Text and products are separate on purpose: ``message`` is what the chat bubble says,
    ``product_ids`` is what the website shows as product cards in the Spotlight.
    """
    message: str = Field(
        description="Chat reply in the Campus Customs voice. Short; light Markdown (bold, bullet "
                    "lists) is fine. Don't list every product - the cards show them. No images or links.",
    )
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=MAX_SHOWCASE,
        description="Products to show on the page as cards, most relevant first (up to 12). Only "
                    "ids returned by your tools. Empty for small talk or when nothing fits.",
    )
    showcase_title: str | None = Field(
        default=None,
        max_length=60,
        description="Short heading for the cards, e.g. 'Hoodies' or 'Gifts for a Yale Dad under $60'. "
                    "Set it whenever product_ids is not empty.",
    )


# ---------- chat API (the contract with the front end) ----------

class PageContext(CamelModel):
    """Where the shopper is when they send a message (sent by the browser with every message).

    Only raw locators come from the browser. The server parses and checks them against the
    database, so product names and details the agent sees always come from the catalogue.
    """
    path: str = Field(default="/", max_length=300, description="Current URL path + query, e.g. /products/saybrook-college-crewneck")
    spotlight_product_ids: list[str] = Field(
        default_factory=list, max_length=12,
        description="Products currently shown in the Spotlight, in on-screen order.")
    spotlight_title: str | None = Field(default=None, max_length=60)


class ChatRequest(CamelModel):
    message: str = Field(min_length=1, max_length=1000)
    page: PageContext | None = None


class AssistantMessage(CamelModel):
    """The chat text only. Never contains product data."""
    role: Literal["assistant"] = "assistant"
    content: str


class Showcase(CamelModel):
    """Products the website renders as cards in the Spotlight (not inside the chat bubble).

    ``products`` are full Product objects - the same shape as GET /api/products - with live
    price and stock, so the site reuses its normal ProductCard and product pages.
    """
    title: str
    products: list[Product]
    total_matches: int | None = Field(
        default=None, description="How many products matched the search behind these cards, if known.")
    browse_url: str | None = Field(
        default=None, description="Products-page URL with the same search, e.g. /products?category=Hoodies.")


class ChatReply(CamelModel):
    """POST /api/chat response: the message and the product data as two separate parts."""
    message: AssistantMessage
    showcase: Showcase | None = None


class ChatHistoryMessage(CamelModel):
    role: Literal["user", "assistant"]
    content: str
    showcase: Showcase | None = None
    created_at: str | None = Field(default=None, description="UTC, 'YYYY-MM-DD HH:MM:SS'.")


class ChatHistory(CamelModel):
    """GET /api/chat/history."""
    saved: bool = Field(description="True for logged-in shoppers (stored in chat_messages); "
                                    "False for guests (kept in memory for this visit only).")
    messages: list[ChatHistoryMessage]


# ---------- what the agent knows about the shopper and the page ----------

class CustomerProfile(BaseModel):
    """The logged-in shopper, from the users table. Given to the agent via AgentDeps."""
    first_name: str
    last_name: str
    email: str
    customer_since: str = Field(description="Account creation date, YYYY-MM-DD.")
    saved_messages: int = Field(description="Messages already in this shopper's saved chat history.")


class PageInfo(BaseModel):
    """The shopper's current page, resolved and validated by the server."""
    page_type: Literal["home", "products", "product", "about", "account", "other"]
    path: str
    product: ProductRef | None = Field(default=None, description="Set on a product page: the item 'this' refers to.")
    products_filter: str | None = Field(default=None, description="Search/filters active on the Products page.")
    spotlight_title: str | None = None
    spotlight: list[ProductRef] = Field(default_factory=list, description="Cards in the Spotlight, in order.")


# ---------- cart & checkout (reserve for in-store pickup) ----------

MAX_LINE_QTY = 10
MAX_CART_LINES = 20


class CartLineIn(CamelModel):
    product_id: str = Field(max_length=200)
    size: Literal["XS", "S", "M", "L", "XL", "XXL"]
    quantity: int = Field(ge=1, le=MAX_LINE_QTY)


class CartIn(CamelModel):
    items: list[CartLineIn] = Field(max_length=MAX_CART_LINES)


class CartLineQuote(CamelModel):
    """A cart line priced and checked against live stock."""
    product_id: str
    size: str
    quantity: int
    name: str | None = None
    image: str | None = None
    unit_price: float | None = None
    line_total: float | None = None
    available: int = Field(description="Units in stock for this size right now.")
    problem: Literal["unknown_product", "sold_out", "not_enough_stock"] | None = None


class CartQuote(CamelModel):
    lines: list[CartLineQuote]
    item_count: int
    subtotal: float
    ok: bool = Field(description="True when every line can be reserved as-is.")


class CheckoutIn(CartIn):
    pickup_name: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=300)


class OrderItemOut(CamelModel):
    product_id: str
    name: str
    size: str
    quantity: int
    unit_price: float
    image: str


class OrderOut(CamelModel):
    order_number: str
    status: str
    pickup_name: str
    note: str | None
    item_count: int
    subtotal: float
    created_at: str
    items: list[OrderItemOut]
