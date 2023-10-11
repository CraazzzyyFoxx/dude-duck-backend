from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "timestampmixin" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS "user" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "email" VARCHAR(100) NOT NULL UNIQUE,
    "hashed_password" TEXT NOT NULL,
    "is_active" BOOL NOT NULL  DEFAULT True,
    "is_superuser" BOOL NOT NULL  DEFAULT False,
    "is_verified" BOOL NOT NULL  DEFAULT False,
    "name" VARCHAR(20) NOT NULL UNIQUE,
    "telegram" VARCHAR(32) NOT NULL UNIQUE,
    "phone" TEXT,
    "bank" TEXT,
    "bankcard" TEXT,
    "binance_email" TEXT,
    "binance_id" INT,
    "discord" TEXT,
    "language" VARCHAR(2) NOT NULL  DEFAULT 'en',
    "google" JSONB,
    "max_orders" INT NOT NULL  DEFAULT 3
);
COMMENT ON COLUMN "user"."language" IS 'RU: ru\nEN: en';
CREATE TABLE IF NOT EXISTS "accesstoken" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "token" VARCHAR(100) NOT NULL UNIQUE,
    "user_id" BIGINT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "accesstokenapi" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "token" VARCHAR(100) NOT NULL UNIQUE,
    "user_id" BIGINT NOT NULL UNIQUE REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "currency" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "date" TIMESTAMPTZ NOT NULL UNIQUE,
    "timestamp" INT NOT NULL,
    "quotes" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "order" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "order_id" VARCHAR(10) NOT NULL UNIQUE,
    "spreadsheet" TEXT NOT NULL,
    "sheet_id" BIGINT NOT NULL,
    "row_id" BIGINT NOT NULL,
    "date" TIMESTAMPTZ NOT NULL,
    "shop" TEXT,
    "shop_order_id" TEXT,
    "contact" TEXT,
    "screenshot" TEXT,
    "status" VARCHAR(11) NOT NULL,
    "status_paid" VARCHAR(8) NOT NULL,
    "auth_date" TIMESTAMPTZ,
    "end_date" TIMESTAMPTZ
);
COMMENT ON COLUMN "order"."status" IS 'Refund: Refund\nInProgress: In Progress\nCompleted: Completed';
COMMENT ON COLUMN "order"."status_paid" IS 'Paid: Paid\nNotPaid: Not Paid';
CREATE TABLE IF NOT EXISTS "userorder" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "dollars" DOUBLE PRECISION NOT NULL,
    "completed" BOOL NOT NULL  DEFAULT False,
    "paid" BOOL NOT NULL  DEFAULT False,
    "paid_at" TIMESTAMPTZ,
    "method_payment" VARCHAR(20) NOT NULL  DEFAULT '$',
    "order_date" TIMESTAMPTZ NOT NULL,
    "completed_at" TIMESTAMPTZ,
    "order_id" BIGINT NOT NULL REFERENCES "order" ("id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_userorder_order_i_aa9235" UNIQUE ("order_id", "user_id")
);
CREATE TABLE IF NOT EXISTS "ordercredentials" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "battle_tag" TEXT,
    "nickname" TEXT,
    "login" TEXT,
    "password" TEXT,
    "vpn" TEXT,
    "discord" TEXT,
    "order_id" BIGINT NOT NULL UNIQUE REFERENCES "order" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "orderinfo" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "boost_type" VARCHAR(10) NOT NULL,
    "region_fraction" TEXT,
    "server" TEXT,
    "category" TEXT,
    "character_class" TEXT,
    "platform" VARCHAR(20),
    "game" TEXT NOT NULL,
    "purchase" TEXT NOT NULL,
    "comment" TEXT,
    "eta" TEXT,
    "order_id" BIGINT NOT NULL UNIQUE REFERENCES "order" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "orderprice" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "price_dollar" DOUBLE PRECISION NOT NULL,
    "price_booster_dollar" DOUBLE PRECISION NOT NULL,
    "price_booster_gold" DOUBLE PRECISION,
    "order_id" BIGINT NOT NULL UNIQUE REFERENCES "order" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "preorder" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "order_id" VARCHAR(10) NOT NULL UNIQUE,
    "spreadsheet" TEXT NOT NULL,
    "sheet_id" BIGINT NOT NULL,
    "row_id" BIGINT NOT NULL,
    "date" TIMESTAMPTZ NOT NULL,
    "has_response" BOOL NOT NULL  DEFAULT False
);
CREATE TABLE IF NOT EXISTS "preorderinfo" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "boost_type" VARCHAR(10) NOT NULL,
    "region_fraction" TEXT,
    "server" TEXT,
    "category" TEXT,
    "character_class" TEXT,
    "platform" VARCHAR(20),
    "game" TEXT NOT NULL,
    "purchase" TEXT NOT NULL,
    "comment" TEXT,
    "eta" TEXT,
    "order_id" BIGINT NOT NULL UNIQUE REFERENCES "preorder" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "preorderprice" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "price_dollar" DOUBLE PRECISION NOT NULL,
    "price_booster_dollar" DOUBLE PRECISION NOT NULL,
    "price_booster_gold" DOUBLE PRECISION,
    "order_id" BIGINT NOT NULL UNIQUE REFERENCES "preorder" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "preresponse" (
    "refund" BOOL NOT NULL  DEFAULT False,
    "approved" BOOL NOT NULL  DEFAULT False,
    "closed" BOOL NOT NULL  DEFAULT False,
    "text" TEXT,
    "price" DOUBLE PRECISION,
    "start_date" TIMESTAMPTZ,
    "eta" BIGINT,
    "approved_at" TIMESTAMPTZ,
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "order_id" BIGINT NOT NULL REFERENCES "preorder" ("id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_preresponse_order_i_a28918" UNIQUE ("order_id", "user_id")
);
CREATE TABLE IF NOT EXISTS "response" (
    "refund" BOOL NOT NULL  DEFAULT False,
    "approved" BOOL NOT NULL  DEFAULT False,
    "closed" BOOL NOT NULL  DEFAULT False,
    "text" TEXT,
    "price" DOUBLE PRECISION,
    "start_date" TIMESTAMPTZ,
    "eta" BIGINT,
    "approved_at" TIMESTAMPTZ,
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "order_id" BIGINT NOT NULL REFERENCES "order" ("id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_response_order_i_6b9689" UNIQUE ("order_id", "user_id")
);
CREATE TABLE IF NOT EXISTS "settings" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "api_layer_currency" JSONB NOT NULL,
    "currencies" JSONB NOT NULL,
    "preorder_time_alive" INT NOT NULL  DEFAULT 60,
    "accounting_fee" DOUBLE PRECISION NOT NULL  DEFAULT 0.95,
    "currency_wow" DOUBLE PRECISION NOT NULL  DEFAULT 0.031,
    "collect_currency_wow_by_sheets" BOOL NOT NULL  DEFAULT False,
    "currency_wow_spreadsheet" TEXT,
    "currency_wow_sheet_id" BIGINT,
    "currency_wow_cell" TEXT
);
CREATE TABLE IF NOT EXISTS "ordersheetparse" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ,
    "spreadsheet" TEXT NOT NULL,
    "sheet_id" BIGINT NOT NULL,
    "start" INT NOT NULL  DEFAULT 2,
    "items" JSONB NOT NULL,
    "is_user" BOOL NOT NULL  DEFAULT False,
    CONSTRAINT "uid_ordersheetp_spreads_976790" UNIQUE ("spreadsheet", "sheet_id")
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
