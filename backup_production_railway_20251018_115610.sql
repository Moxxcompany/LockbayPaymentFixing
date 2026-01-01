--
-- PostgreSQL database dump
--

-- Dumped from database version 16.9 (165f042)
-- Dumped by pg_dump version 17.5

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: _system; Type: SCHEMA; Schema: -; Owner: neondb_owner
--

CREATE SCHEMA _system;


ALTER SCHEMA _system OWNER TO neondb_owner;

--
-- Name: update_balance_alert_state_updated_at(); Type: FUNCTION; Schema: public; Owner: neondb_owner
--

CREATE FUNCTION public.update_balance_alert_state_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_balance_alert_state_updated_at() OWNER TO neondb_owner;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: replit_database_migrations_v1; Type: TABLE; Schema: _system; Owner: neondb_owner
--

CREATE TABLE _system.replit_database_migrations_v1 (
    id bigint NOT NULL,
    build_id text NOT NULL,
    deployment_id text NOT NULL,
    statement_count bigint NOT NULL,
    applied_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE _system.replit_database_migrations_v1 OWNER TO neondb_owner;

--
-- Name: replit_database_migrations_v1_id_seq; Type: SEQUENCE; Schema: _system; Owner: neondb_owner
--

CREATE SEQUENCE _system.replit_database_migrations_v1_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE _system.replit_database_migrations_v1_id_seq OWNER TO neondb_owner;

--
-- Name: replit_database_migrations_v1_id_seq; Type: SEQUENCE OWNED BY; Schema: _system; Owner: neondb_owner
--

ALTER SEQUENCE _system.replit_database_migrations_v1_id_seq OWNED BY _system.replit_database_migrations_v1.id;


--
-- Name: admin_action_tokens; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.admin_action_tokens (
    id integer NOT NULL,
    token character varying(64) NOT NULL,
    action character varying(20) NOT NULL,
    cashout_id character varying(20) NOT NULL,
    admin_email character varying(255) NOT NULL,
    admin_user_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    used_by_ip character varying(45),
    used_by_user_agent text,
    action_result character varying(20),
    error_message text,
    completed_at timestamp with time zone
);


ALTER TABLE public.admin_action_tokens OWNER TO neondb_owner;

--
-- Name: admin_action_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.admin_action_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.admin_action_tokens_id_seq OWNER TO neondb_owner;

--
-- Name: admin_action_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.admin_action_tokens_id_seq OWNED BY public.admin_action_tokens.id;


--
-- Name: admin_operation_overrides; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.admin_operation_overrides (
    id integer NOT NULL,
    provider character varying(50) NOT NULL,
    operation_type character varying(50),
    override_type character varying(20) NOT NULL,
    reason text,
    created_by character varying(100),
    is_active boolean NOT NULL,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.admin_operation_overrides OWNER TO neondb_owner;

--
-- Name: admin_operation_overrides_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.admin_operation_overrides_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.admin_operation_overrides_id_seq OWNER TO neondb_owner;

--
-- Name: admin_operation_overrides_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.admin_operation_overrides_id_seq OWNED BY public.admin_operation_overrides.id;


--
-- Name: audit_events; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.audit_events (
    id integer NOT NULL,
    event_id character varying(36) NOT NULL,
    event_type character varying(50) NOT NULL,
    entity_type character varying(50) NOT NULL,
    entity_id character varying(50) NOT NULL,
    event_data jsonb NOT NULL,
    user_id bigint,
    processed boolean NOT NULL,
    processed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.audit_events OWNER TO neondb_owner;

--
-- Name: audit_events_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.audit_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_events_id_seq OWNER TO neondb_owner;

--
-- Name: audit_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.audit_events_id_seq OWNED BY public.audit_events.id;


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.audit_logs (
    id integer NOT NULL,
    event_type character varying(50) NOT NULL,
    entity_type character varying(50) NOT NULL,
    entity_id character varying(50) NOT NULL,
    user_id bigint,
    admin_id bigint,
    previous_state jsonb,
    new_state jsonb,
    changes jsonb,
    description text,
    ip_address character varying(45),
    user_agent text,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.audit_logs OWNER TO neondb_owner;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_logs_id_seq OWNER TO neondb_owner;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: balance_alert_state; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.balance_alert_state (
    id integer NOT NULL,
    alert_key character varying(200) NOT NULL,
    provider character varying(50) NOT NULL,
    currency character varying(10) NOT NULL,
    alert_level character varying(50) NOT NULL,
    last_alert_time timestamp with time zone NOT NULL,
    alert_count integer DEFAULT 1,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.balance_alert_state OWNER TO neondb_owner;

--
-- Name: balance_alert_state_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.balance_alert_state_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.balance_alert_state_id_seq OWNER TO neondb_owner;

--
-- Name: balance_alert_state_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.balance_alert_state_id_seq OWNED BY public.balance_alert_state.id;


--
-- Name: balance_audit_logs; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.balance_audit_logs (
    id integer NOT NULL,
    audit_id character varying(100) NOT NULL,
    wallet_type character varying(20) NOT NULL,
    user_id bigint,
    wallet_id integer,
    internal_wallet_id character varying(100),
    currency character varying(10) NOT NULL,
    balance_type character varying(20) NOT NULL,
    amount_before numeric(20,8) NOT NULL,
    amount_after numeric(20,8) NOT NULL,
    change_amount numeric(20,8) NOT NULL,
    change_type character varying(10) NOT NULL,
    transaction_id character varying(100),
    transaction_type character varying(50) NOT NULL,
    operation_type character varying(50) NOT NULL,
    initiated_by character varying(50) NOT NULL,
    initiated_by_id character varying(100),
    reason text NOT NULL,
    escrow_pk integer,
    escrow_id character varying(20),
    cashout_id character varying(100),
    exchange_id character varying(100),
    balance_validation_passed boolean NOT NULL,
    pre_validation_checksum character varying(64),
    post_validation_checksum character varying(64),
    idempotency_key character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    processed_at timestamp with time zone,
    audit_metadata text,
    ip_address character varying(45),
    user_agent character varying(500),
    api_version character varying(20),
    hostname character varying(100),
    process_id character varying(50),
    thread_id character varying(50),
    CONSTRAINT chk_non_zero_change CHECK ((change_amount <> (0)::numeric)),
    CONSTRAINT chk_valid_balance_type CHECK (((balance_type)::text = ANY (ARRAY[('available'::character varying)::text, ('frozen'::character varying)::text, ('locked'::character varying)::text, ('reserved'::character varying)::text]))),
    CONSTRAINT chk_valid_change_type CHECK (((change_type)::text = ANY (ARRAY[('credit'::character varying)::text, ('debit'::character varying)::text]))),
    CONSTRAINT chk_valid_wallet_type CHECK (((wallet_type)::text = ANY (ARRAY[('user'::character varying)::text, ('internal'::character varying)::text])))
);


ALTER TABLE public.balance_audit_logs OWNER TO neondb_owner;

--
-- Name: balance_audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.balance_audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.balance_audit_logs_id_seq OWNER TO neondb_owner;

--
-- Name: balance_audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.balance_audit_logs_id_seq OWNED BY public.balance_audit_logs.id;


--
-- Name: balance_protection_logs; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.balance_protection_logs (
    id integer NOT NULL,
    operation_type character varying(50) NOT NULL,
    currency character varying(10) NOT NULL,
    amount numeric(20,8) NOT NULL,
    user_id bigint,
    operation_allowed boolean NOT NULL,
    alert_level character varying(20),
    balance_check_passed boolean NOT NULL,
    insufficient_services text,
    warning_message text,
    blocking_reason text,
    fincra_balance double precision,
    kraken_balances jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.balance_protection_logs OWNER TO neondb_owner;

--
-- Name: balance_protection_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.balance_protection_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.balance_protection_logs_id_seq OWNER TO neondb_owner;

--
-- Name: balance_protection_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.balance_protection_logs_id_seq OWNED BY public.balance_protection_logs.id;


--
-- Name: balance_reconciliation_logs; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.balance_reconciliation_logs (
    id integer NOT NULL,
    reconciliation_id character varying(100) NOT NULL,
    reconciliation_type character varying(50) NOT NULL,
    target_type character varying(20) NOT NULL,
    user_id bigint,
    internal_wallet_id character varying(100),
    currency character varying(10),
    status character varying(50) NOT NULL,
    discrepancies_found integer NOT NULL,
    discrepancies_resolved integer NOT NULL,
    total_amount_discrepancy numeric(20,8) NOT NULL,
    wallets_checked integer NOT NULL,
    transactions_verified integer NOT NULL,
    snapshots_created integer NOT NULL,
    audit_logs_created integer NOT NULL,
    started_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    duration_seconds integer,
    triggered_by character varying(50) NOT NULL,
    triggered_by_id character varying(100),
    trigger_reason character varying(200),
    findings_summary text,
    actions_taken text,
    recommendations text,
    error_count integer NOT NULL,
    last_error_message text,
    warning_count integer NOT NULL,
    hostname character varying(100),
    process_id character varying(50),
    version character varying(20),
    configuration text,
    reconciliation_metadata text,
    notes text,
    CONSTRAINT chk_valid_reconciliation_status CHECK (((status)::text = ANY (ARRAY[('started'::character varying)::text, ('completed'::character varying)::text, ('failed'::character varying)::text, ('partial'::character varying)::text]))),
    CONSTRAINT chk_valid_resolution_count CHECK ((discrepancies_resolved <= discrepancies_found)),
    CONSTRAINT chk_valid_target_type CHECK (((target_type)::text = ANY (ARRAY[('user'::character varying)::text, ('internal'::character varying)::text, ('all'::character varying)::text])))
);


ALTER TABLE public.balance_reconciliation_logs OWNER TO neondb_owner;

--
-- Name: balance_reconciliation_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.balance_reconciliation_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.balance_reconciliation_logs_id_seq OWNER TO neondb_owner;

--
-- Name: balance_reconciliation_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.balance_reconciliation_logs_id_seq OWNED BY public.balance_reconciliation_logs.id;


--
-- Name: cashouts; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.cashouts (
    id integer NOT NULL,
    cashout_id character varying(16) NOT NULL,
    user_id bigint NOT NULL,
    amount numeric(38,18) NOT NULL,
    currency character varying(10) NOT NULL,
    cashout_type character varying(20) NOT NULL,
    destination_type character varying(20) NOT NULL,
    destination_address character varying(255),
    bank_details jsonb,
    network_fee numeric(38,18) NOT NULL,
    platform_fee numeric(38,18) NOT NULL,
    net_amount numeric(38,18) NOT NULL,
    pricing_snapshot jsonb,
    status character varying(20) NOT NULL,
    provider character varying(20),
    external_id character varying(100),
    external_reference character varying(100),
    admin_approved boolean NOT NULL,
    admin_notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    processed_at timestamp with time zone,
    completed_at timestamp with time zone,
    error_message text,
    retry_count integer NOT NULL,
    utid character varying(32),
    destination character varying(50),
    bank_account_id integer,
    cashout_metadata jsonb,
    external_tx_id character varying(255),
    fincra_request_id character varying(255),
    processing_mode character varying(50),
    failure_type character varying(20),
    last_error_code character varying(50),
    failed_at timestamp with time zone,
    technical_failure_since timestamp with time zone,
    CONSTRAINT ck_cashout_amount_positive CHECK ((amount > (0)::numeric)),
    CONSTRAINT ck_cashout_net_amount_positive CHECK ((net_amount > (0)::numeric)),
    CONSTRAINT ck_cashout_net_equals_calculation CHECK ((net_amount = ((amount - network_fee) - platform_fee))),
    CONSTRAINT ck_cashout_network_fee_positive CHECK ((network_fee >= (0)::numeric)),
    CONSTRAINT ck_cashout_platform_fee_positive CHECK ((platform_fee >= (0)::numeric)),
    CONSTRAINT ck_cashout_status_valid CHECK (((status)::text = ANY (ARRAY[('pending'::character varying)::text, ('otp_pending'::character varying)::text, ('user_confirm_pending'::character varying)::text, ('admin_pending'::character varying)::text, ('approved'::character varying)::text, ('admin_approved'::character varying)::text, ('awaiting_response'::character varying)::text, ('pending_address_config'::character varying)::text, ('pending_service_funding'::character varying)::text, ('executing'::character varying)::text, ('processing'::character varying)::text, ('completed'::character varying)::text, ('success'::character varying)::text, ('failed'::character varying)::text, ('expired'::character varying)::text, ('cancelled'::character varying)::text]))),
    CONSTRAINT ck_cashout_type_valid CHECK (((cashout_type)::text = ANY (ARRAY[('crypto'::character varying)::text, ('ngn_bank'::character varying)::text])))
);


ALTER TABLE public.cashouts OWNER TO neondb_owner;

--
-- Name: cashouts_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.cashouts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cashouts_id_seq OWNER TO neondb_owner;

--
-- Name: cashouts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.cashouts_id_seq OWNED BY public.cashouts.id;


--
-- Name: crypto_deposits; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.crypto_deposits (
    id integer NOT NULL,
    provider character varying(20) NOT NULL,
    txid character varying(100) NOT NULL,
    order_id character varying(50),
    address_in character varying(200) NOT NULL,
    address_out character varying(200),
    coin character varying(10) NOT NULL,
    amount numeric(20,8) NOT NULL,
    amount_fiat numeric(20,8),
    confirmations integer NOT NULL,
    required_confirmations integer NOT NULL,
    status character varying(25) NOT NULL,
    user_id bigint,
    created_at timestamp without time zone NOT NULL,
    confirmed_at timestamp without time zone,
    credited_at timestamp without time zone
);


ALTER TABLE public.crypto_deposits OWNER TO neondb_owner;

--
-- Name: crypto_deposits_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.crypto_deposits_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.crypto_deposits_id_seq OWNER TO neondb_owner;

--
-- Name: crypto_deposits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.crypto_deposits_id_seq OWNED BY public.crypto_deposits.id;


--
-- Name: dispute_messages; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.dispute_messages (
    id integer NOT NULL,
    dispute_id integer NOT NULL,
    sender_id bigint NOT NULL,
    message text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.dispute_messages OWNER TO neondb_owner;

--
-- Name: dispute_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.dispute_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dispute_messages_id_seq OWNER TO neondb_owner;

--
-- Name: dispute_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.dispute_messages_id_seq OWNED BY public.dispute_messages.id;


--
-- Name: disputes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.disputes (
    id integer NOT NULL,
    escrow_id integer,
    initiator_id bigint,
    respondent_id bigint,
    dispute_type character varying(255) NOT NULL,
    reason text,
    status character varying(255),
    admin_assigned_id bigint,
    resolution text,
    resolved_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.disputes OWNER TO neondb_owner;

--
-- Name: disputes_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.disputes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.disputes_id_seq OWNER TO neondb_owner;

--
-- Name: disputes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.disputes_id_seq OWNED BY public.disputes.id;


--
-- Name: distributed_locks; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.distributed_locks (
    id integer NOT NULL,
    lock_name character varying(255) NOT NULL,
    locked_by character varying(255),
    locked_at timestamp without time zone DEFAULT now(),
    expires_at timestamp without time zone NOT NULL,
    metadata jsonb
);


ALTER TABLE public.distributed_locks OWNER TO neondb_owner;

--
-- Name: distributed_locks_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.distributed_locks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.distributed_locks_id_seq OWNER TO neondb_owner;

--
-- Name: distributed_locks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.distributed_locks_id_seq OWNED BY public.distributed_locks.id;


--
-- Name: email_verifications; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.email_verifications (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    email character varying(255) NOT NULL,
    verification_code character varying(10) NOT NULL,
    purpose character varying(50) NOT NULL,
    verified boolean NOT NULL,
    attempts integer NOT NULL,
    max_attempts integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    verified_at timestamp with time zone,
    deleted_at timestamp with time zone
);


ALTER TABLE public.email_verifications OWNER TO neondb_owner;

--
-- Name: email_verifications_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.email_verifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.email_verifications_id_seq OWNER TO neondb_owner;

--
-- Name: email_verifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.email_verifications_id_seq OWNED BY public.email_verifications.id;


--
-- Name: escrow_holdings; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.escrow_holdings (
    id integer NOT NULL,
    escrow_id character varying(50) NOT NULL,
    amount_held numeric(20,8) NOT NULL,
    currency character varying(10) NOT NULL,
    overpayment_amount numeric(20,8),
    overpayment_currency character varying(10),
    overpayment_usd_value numeric(20,8),
    overpayment_transaction_id character varying(100),
    original_amount numeric(20,8),
    total_released numeric(20,8) NOT NULL,
    remaining_amount numeric(20,8),
    partial_releases_count integer NOT NULL,
    created_at timestamp without time zone,
    released_at timestamp without time zone,
    first_release_at timestamp without time zone,
    released_to_user_id bigint,
    status character varying(20)
);


ALTER TABLE public.escrow_holdings OWNER TO neondb_owner;

--
-- Name: escrow_holdings_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.escrow_holdings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.escrow_holdings_id_seq OWNER TO neondb_owner;

--
-- Name: escrow_holdings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.escrow_holdings_id_seq OWNED BY public.escrow_holdings.id;


--
-- Name: escrow_messages; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.escrow_messages (
    id integer NOT NULL,
    escrow_id integer,
    sender_id bigint,
    content text NOT NULL,
    message_type character varying(255),
    attachments jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.escrow_messages OWNER TO neondb_owner;

--
-- Name: escrow_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.escrow_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.escrow_messages_id_seq OWNER TO neondb_owner;

--
-- Name: escrow_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.escrow_messages_id_seq OWNED BY public.escrow_messages.id;


--
-- Name: escrow_refund_operations; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.escrow_refund_operations (
    id integer NOT NULL,
    escrow_id integer NOT NULL,
    buyer_id bigint NOT NULL,
    refund_cycle_id character varying(64) NOT NULL,
    refund_reason character varying(100) NOT NULL,
    amount_refunded numeric(38,18) NOT NULL,
    currency character varying(10) NOT NULL,
    transaction_id character varying(50),
    idempotency_key character varying(128) NOT NULL,
    processed_by_service character varying(100) NOT NULL,
    processing_context jsonb,
    status character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_escrow_refund_amount_positive CHECK ((amount_refunded > (0)::numeric))
);


ALTER TABLE public.escrow_refund_operations OWNER TO neondb_owner;

--
-- Name: escrow_refund_operations_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.escrow_refund_operations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.escrow_refund_operations_id_seq OWNER TO neondb_owner;

--
-- Name: escrow_refund_operations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.escrow_refund_operations_id_seq OWNED BY public.escrow_refund_operations.id;


--
-- Name: escrows; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.escrows (
    id integer NOT NULL,
    escrow_id character varying(16) NOT NULL,
    utid character varying(32),
    buyer_id bigint NOT NULL,
    seller_id bigint,
    seller_email character varying(255),
    seller_contact_type character varying(20),
    seller_contact_value character varying(255),
    seller_contact_display character varying(255),
    amount numeric(38,18) NOT NULL,
    currency character varying(10) NOT NULL,
    fee_amount numeric(38,18) NOT NULL,
    total_amount numeric(38,18) NOT NULL,
    pricing_snapshot jsonb,
    description text,
    payment_method character varying(20),
    deposit_address character varying(100),
    deposit_tx_hash character varying(100),
    status character varying(20) NOT NULL,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    payment_confirmed_at timestamp with time zone,
    completed_at timestamp with time zone,
    delivery_deadline timestamp with time zone,
    auto_release_at timestamp with time zone,
    admin_notes text,
    dispute_reason text,
    fee_split_option character varying(20) DEFAULT 'buyer_pays'::character varying NOT NULL,
    buyer_fee_amount numeric(38,18) DEFAULT 0 NOT NULL,
    seller_fee_amount numeric(38,18) DEFAULT 0 NOT NULL,
    seller_accepted_at timestamp with time zone,
    delivered_at timestamp with time zone,
    warning_24h_sent boolean DEFAULT false NOT NULL,
    warning_8h_sent boolean DEFAULT false NOT NULL,
    warning_2h_sent boolean DEFAULT false NOT NULL,
    warning_30m_sent boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_escrow_amount_positive CHECK ((amount > (0)::numeric)),
    CONSTRAINT ck_escrow_buyer_fee_positive CHECK ((buyer_fee_amount >= (0)::numeric)),
    CONSTRAINT ck_escrow_contact_type_valid CHECK (((seller_contact_type IS NULL) OR ((seller_contact_type)::text = ANY (ARRAY[('username'::character varying)::text, ('email'::character varying)::text, ('phone'::character varying)::text])))),
    CONSTRAINT ck_escrow_fee_positive CHECK ((fee_amount >= (0)::numeric)),
    CONSTRAINT ck_escrow_fee_split_sum CHECK ((fee_amount = (buyer_fee_amount + seller_fee_amount))),
    CONSTRAINT ck_escrow_fee_split_valid CHECK (((fee_split_option)::text = ANY (ARRAY[('buyer_pays'::character varying)::text, ('seller_pays'::character varying)::text, ('split'::character varying)::text]))),
    CONSTRAINT ck_escrow_id_consistency CHECK (((utid)::text = (escrow_id)::text)),
    CONSTRAINT ck_escrow_seller_assigned CHECK (((seller_id IS NOT NULL) OR ((seller_contact_type IS NOT NULL) AND (seller_contact_value IS NOT NULL)))),
    CONSTRAINT ck_escrow_seller_fee_positive CHECK ((seller_fee_amount >= (0)::numeric)),
    CONSTRAINT ck_escrow_status_valid CHECK (((status)::text = ANY (ARRAY[('created'::character varying)::text, ('payment_pending'::character varying)::text, ('payment_confirmed'::character varying)::text, ('partial_payment'::character varying)::text, ('payment_failed'::character varying)::text, ('active'::character varying)::text, ('completed'::character varying)::text, ('disputed'::character varying)::text, ('refunded'::character varying)::text, ('cancelled'::character varying)::text, ('expired'::character varying)::text]))),
    CONSTRAINT ck_escrow_total_equals_sum CHECK ((total_amount = (amount + fee_amount))),
    CONSTRAINT ck_escrow_total_positive CHECK ((total_amount > (0)::numeric))
);


ALTER TABLE public.escrows OWNER TO neondb_owner;

--
-- Name: escrows_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.escrows_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.escrows_id_seq OWNER TO neondb_owner;

--
-- Name: escrows_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.escrows_id_seq OWNED BY public.escrows.id;


--
-- Name: exchange_orders; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.exchange_orders (
    id integer NOT NULL,
    utid character varying(50),
    exchange_id character varying(20),
    user_id bigint NOT NULL,
    order_type character varying(50) NOT NULL,
    source_currency character varying(10) NOT NULL,
    source_amount numeric(20,8) NOT NULL,
    source_network character varying(50),
    target_currency character varying(10) NOT NULL,
    target_amount numeric(20,8) NOT NULL,
    target_network character varying(50),
    exchange_rate numeric(20,8) NOT NULL,
    markup_percentage numeric(5,2) NOT NULL,
    fee_amount numeric(20,8) NOT NULL,
    final_amount numeric(20,8) NOT NULL,
    usd_equivalent numeric(20,8),
    rate_locked_at timestamp with time zone,
    rate_lock_expires_at timestamp with time zone,
    rate_lock_duration_minutes integer,
    crypto_address character varying(200),
    bank_account text,
    wallet_address character varying(200),
    deposit_tx_hash character varying(200),
    payout_tx_hash character varying(200),
    bank_reference character varying(100),
    status character varying(255),
    provider character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    expires_at timestamp with time zone
);


ALTER TABLE public.exchange_orders OWNER TO neondb_owner;

--
-- Name: exchange_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.exchange_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.exchange_orders_id_seq OWNER TO neondb_owner;

--
-- Name: exchange_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.exchange_orders_id_seq OWNED BY public.exchange_orders.id;


--
-- Name: idempotency_keys; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.idempotency_keys (
    id integer NOT NULL,
    operation_key character varying(255) NOT NULL,
    user_id bigint,
    operation_type character varying(50) NOT NULL,
    entity_id character varying(50),
    result_data jsonb,
    success boolean,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL
);


ALTER TABLE public.idempotency_keys OWNER TO neondb_owner;

--
-- Name: idempotency_keys_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.idempotency_keys_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.idempotency_keys_id_seq OWNER TO neondb_owner;

--
-- Name: idempotency_keys_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.idempotency_keys_id_seq OWNED BY public.idempotency_keys.id;


--
-- Name: idempotency_tokens; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.idempotency_tokens (
    id integer NOT NULL,
    idempotency_key character varying(255) NOT NULL,
    operation_type character varying(100) NOT NULL,
    resource_id character varying(255) NOT NULL,
    status character varying(50) NOT NULL,
    result_data text,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    expires_at timestamp with time zone NOT NULL,
    metadata_json text
);


ALTER TABLE public.idempotency_tokens OWNER TO neondb_owner;

--
-- Name: idempotency_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.idempotency_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.idempotency_tokens_id_seq OWNER TO neondb_owner;

--
-- Name: idempotency_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.idempotency_tokens_id_seq OWNED BY public.idempotency_tokens.id;


--
-- Name: inbox_webhooks; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.inbox_webhooks (
    id integer NOT NULL,
    webhook_id character varying(100) NOT NULL,
    provider character varying(20) NOT NULL,
    event_type character varying(50) NOT NULL,
    status character varying(20) NOT NULL,
    raw_payload jsonb NOT NULL,
    processed_data jsonb,
    transaction_id character varying(50),
    user_id bigint,
    first_received_at timestamp with time zone DEFAULT now() NOT NULL,
    processed_at timestamp with time zone,
    retry_count integer NOT NULL,
    last_error text,
    error_details jsonb
);


ALTER TABLE public.inbox_webhooks OWNER TO neondb_owner;

--
-- Name: inbox_webhooks_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.inbox_webhooks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inbox_webhooks_id_seq OWNER TO neondb_owner;

--
-- Name: inbox_webhooks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.inbox_webhooks_id_seq OWNED BY public.inbox_webhooks.id;


--
-- Name: internal_wallets; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.internal_wallets (
    id integer NOT NULL,
    wallet_id character varying(100) NOT NULL,
    provider_name character varying(50) NOT NULL,
    currency character varying(10) NOT NULL,
    provider_account_id character varying(100),
    available_balance numeric(20,8) NOT NULL,
    locked_balance numeric(20,8) NOT NULL,
    reserved_balance numeric(20,8) NOT NULL,
    total_balance numeric(20,8) NOT NULL,
    minimum_balance numeric(20,8) NOT NULL,
    withdrawal_limit numeric(20,8),
    daily_limit numeric(20,8),
    is_active boolean NOT NULL,
    auto_reconcile boolean NOT NULL,
    emergency_freeze boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    last_reconciled_at timestamp with time zone,
    last_balance_check_at timestamp with time zone,
    version integer NOT NULL,
    configuration text,
    notes text
);


ALTER TABLE public.internal_wallets OWNER TO neondb_owner;

--
-- Name: internal_wallets_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.internal_wallets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.internal_wallets_id_seq OWNER TO neondb_owner;

--
-- Name: internal_wallets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.internal_wallets_id_seq OWNED BY public.internal_wallets.id;


--
-- Name: notification_activities; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.notification_activities (
    id integer NOT NULL,
    activity_id character varying(50) NOT NULL,
    user_id bigint NOT NULL,
    notification_type character varying(50) NOT NULL,
    channel_type character varying(20) NOT NULL,
    channel_value character varying(255) NOT NULL,
    sent_at timestamp without time zone NOT NULL,
    delivered_at timestamp without time zone,
    opened_at timestamp without time zone,
    clicked_at timestamp without time zone,
    response_time integer,
    delivery_status character varying(20) NOT NULL,
    engagement_level character varying(20) NOT NULL,
    priority_score double precision NOT NULL,
    device_type character varying(20),
    location_context character varying(100),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    idempotency_key character varying(255)
);


ALTER TABLE public.notification_activities OWNER TO neondb_owner;

--
-- Name: notification_activities_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.notification_activities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notification_activities_id_seq OWNER TO neondb_owner;

--
-- Name: notification_activities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.notification_activities_id_seq OWNED BY public.notification_activities.id;


--
-- Name: notification_preferences; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.notification_preferences (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    telegram_enabled boolean NOT NULL,
    email_enabled boolean NOT NULL,
    escrow_updates boolean NOT NULL,
    payment_notifications boolean NOT NULL,
    dispute_notifications boolean NOT NULL,
    marketing_emails boolean NOT NULL,
    security_alerts boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.notification_preferences OWNER TO neondb_owner;

--
-- Name: notification_preferences_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.notification_preferences_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notification_preferences_id_seq OWNER TO neondb_owner;

--
-- Name: notification_preferences_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.notification_preferences_id_seq OWNED BY public.notification_preferences.id;


--
-- Name: notification_queue; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.notification_queue (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    channel character varying(20) NOT NULL,
    recipient character varying(255) NOT NULL,
    subject character varying(255),
    content text NOT NULL,
    template_name character varying(100),
    template_data jsonb,
    status character varying(20) NOT NULL,
    priority integer NOT NULL,
    scheduled_at timestamp with time zone DEFAULT now() NOT NULL,
    sent_at timestamp with time zone,
    retry_count integer NOT NULL,
    error_message text,
    idempotency_key character varying(255)
);


ALTER TABLE public.notification_queue OWNER TO neondb_owner;

--
-- Name: notification_queue_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.notification_queue_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notification_queue_id_seq OWNER TO neondb_owner;

--
-- Name: notification_queue_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.notification_queue_id_seq OWNED BY public.notification_queue.id;


--
-- Name: onboarding_sessions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.onboarding_sessions (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    current_step character varying(20) NOT NULL,
    email character varying(255),
    invite_token character varying(100),
    context_data jsonb,
    ip_address character varying(45),
    user_agent character varying(500),
    referral_source character varying(100),
    email_captured_at timestamp with time zone,
    otp_verified_at timestamp with time zone,
    terms_accepted_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL
);


ALTER TABLE public.onboarding_sessions OWNER TO neondb_owner;

--
-- Name: onboarding_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.onboarding_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.onboarding_sessions_id_seq OWNER TO neondb_owner;

--
-- Name: onboarding_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.onboarding_sessions_id_seq OWNED BY public.onboarding_sessions.id;


--
-- Name: otp_verifications; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.otp_verifications (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    email character varying(255) NOT NULL,
    otp_code character varying(10) NOT NULL,
    verification_type character varying(50) NOT NULL,
    context_data text,
    is_verified boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL
);


ALTER TABLE public.otp_verifications OWNER TO neondb_owner;

--
-- Name: otp_verifications_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.otp_verifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.otp_verifications_id_seq OWNER TO neondb_owner;

--
-- Name: otp_verifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.otp_verifications_id_seq OWNED BY public.otp_verifications.id;


--
-- Name: outbox_events; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.outbox_events (
    id integer NOT NULL,
    event_type character varying(50) NOT NULL,
    aggregate_id character varying(100) NOT NULL,
    event_data jsonb NOT NULL,
    processed boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    processed_at timestamp with time zone,
    retry_count integer NOT NULL,
    last_error text
);


ALTER TABLE public.outbox_events OWNER TO neondb_owner;

--
-- Name: outbox_events_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.outbox_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.outbox_events_id_seq OWNER TO neondb_owner;

--
-- Name: outbox_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.outbox_events_id_seq OWNED BY public.outbox_events.id;


--
-- Name: payment_addresses; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.payment_addresses (
    id integer NOT NULL,
    address character varying(255) NOT NULL,
    currency character varying(10) NOT NULL,
    provider character varying(20) NOT NULL,
    user_id bigint,
    escrow_id integer,
    is_used boolean NOT NULL,
    provider_data jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    used_at timestamp with time zone,
    utid character varying(32)
);


ALTER TABLE public.payment_addresses OWNER TO neondb_owner;

--
-- Name: payment_addresses_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.payment_addresses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payment_addresses_id_seq OWNER TO neondb_owner;

--
-- Name: payment_addresses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.payment_addresses_id_seq OWNED BY public.payment_addresses.id;


--
-- Name: pending_cashouts; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.pending_cashouts (
    id integer NOT NULL,
    token text NOT NULL,
    signature character varying(16) NOT NULL,
    user_id bigint NOT NULL,
    amount numeric(20,8) NOT NULL,
    currency character varying(10) NOT NULL,
    withdrawal_address character varying(255) NOT NULL,
    network character varying(20) NOT NULL,
    fee_amount numeric(20,8),
    net_amount numeric(20,8),
    fee_breakdown text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.pending_cashouts OWNER TO neondb_owner;

--
-- Name: pending_cashouts_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.pending_cashouts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pending_cashouts_id_seq OWNER TO neondb_owner;

--
-- Name: pending_cashouts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.pending_cashouts_id_seq OWNED BY public.pending_cashouts.id;


--
-- Name: platform_revenue; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.platform_revenue (
    id integer NOT NULL,
    escrow_id character varying(50) NOT NULL,
    fee_amount numeric(20,8) NOT NULL,
    fee_currency character varying(10) DEFAULT 'USD'::character varying NOT NULL,
    fee_type character varying(50) NOT NULL,
    source_transaction_id character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.platform_revenue OWNER TO neondb_owner;

--
-- Name: platform_revenue_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.platform_revenue_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.platform_revenue_id_seq OWNER TO neondb_owner;

--
-- Name: platform_revenue_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.platform_revenue_id_seq OWNED BY public.platform_revenue.id;


--
-- Name: ratings; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.ratings (
    id integer NOT NULL,
    escrow_id integer NOT NULL,
    rater_id bigint NOT NULL,
    rated_id bigint,
    rating integer NOT NULL,
    comment text,
    category character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_dispute_rating boolean DEFAULT false,
    dispute_outcome character varying(20),
    dispute_resolution_type character varying(20)
);


ALTER TABLE public.ratings OWNER TO neondb_owner;

--
-- Name: ratings_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.ratings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ratings_id_seq OWNER TO neondb_owner;

--
-- Name: ratings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.ratings_id_seq OWNED BY public.ratings.id;


--
-- Name: refunds; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.refunds (
    id integer NOT NULL,
    refund_id character varying(20) NOT NULL,
    user_id bigint NOT NULL,
    refund_type character varying(20) NOT NULL,
    amount numeric(38,18) NOT NULL,
    currency character varying(10) NOT NULL,
    reason text NOT NULL,
    cashout_id character varying(20),
    escrow_id integer,
    transaction_id character varying(20),
    status character varying(20) NOT NULL,
    idempotency_key character varying(100) NOT NULL,
    processed_by character varying(50) NOT NULL,
    balance_before numeric(38,18) NOT NULL,
    balance_after numeric(38,18) NOT NULL,
    admin_approved boolean NOT NULL,
    admin_approved_by bigint,
    admin_approved_at timestamp with time zone,
    error_message text,
    retry_count integer NOT NULL,
    archived_at timestamp with time zone,
    archive_reason character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    failed_at timestamp with time zone,
    CONSTRAINT positive_refund_amount CHECK ((amount > (0)::numeric))
);


ALTER TABLE public.refunds OWNER TO neondb_owner;

--
-- Name: refunds_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.refunds_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.refunds_id_seq OWNER TO neondb_owner;

--
-- Name: refunds_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.refunds_id_seq OWNED BY public.refunds.id;


--
-- Name: saga_steps; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.saga_steps (
    id integer NOT NULL,
    saga_id character varying(50) NOT NULL,
    step_name character varying(100) NOT NULL,
    status character varying(20) NOT NULL,
    step_data jsonb,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone
);


ALTER TABLE public.saga_steps OWNER TO neondb_owner;

--
-- Name: saga_steps_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.saga_steps_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.saga_steps_id_seq OWNER TO neondb_owner;

--
-- Name: saga_steps_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.saga_steps_id_seq OWNED BY public.saga_steps.id;


--
-- Name: saved_addresses; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.saved_addresses (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    currency character varying(10) NOT NULL,
    network character varying(50),
    address character varying(200) NOT NULL,
    label character varying(100) NOT NULL,
    is_verified boolean NOT NULL,
    verification_sent boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_used timestamp with time zone,
    is_active boolean NOT NULL
);


ALTER TABLE public.saved_addresses OWNER TO neondb_owner;

--
-- Name: saved_addresses_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.saved_addresses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.saved_addresses_id_seq OWNER TO neondb_owner;

--
-- Name: saved_addresses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.saved_addresses_id_seq OWNED BY public.saved_addresses.id;


--
-- Name: saved_bank_accounts; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.saved_bank_accounts (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    account_number character varying(20) NOT NULL,
    bank_code character varying(10) NOT NULL,
    bank_name character varying(100) NOT NULL,
    account_name character varying(200) NOT NULL,
    label character varying(100) NOT NULL,
    is_default boolean NOT NULL,
    is_active boolean NOT NULL,
    is_verified boolean NOT NULL,
    verification_sent boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_used timestamp with time zone
);


ALTER TABLE public.saved_bank_accounts OWNER TO neondb_owner;

--
-- Name: saved_bank_accounts_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.saved_bank_accounts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.saved_bank_accounts_id_seq OWNER TO neondb_owner;

--
-- Name: saved_bank_accounts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.saved_bank_accounts_id_seq OWNED BY public.saved_bank_accounts.id;


--
-- Name: security_audits; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.security_audits (
    id integer NOT NULL,
    user_id bigint,
    action_type character varying(50) NOT NULL,
    resource_type character varying(50),
    resource_id character varying(100),
    ip_address character varying(45),
    user_agent text,
    success boolean NOT NULL,
    risk_level character varying(20) NOT NULL,
    description text,
    context_data jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.security_audits OWNER TO neondb_owner;

--
-- Name: security_audits_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.security_audits_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.security_audits_id_seq OWNER TO neondb_owner;

--
-- Name: security_audits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.security_audits_id_seq OWNED BY public.security_audits.id;


--
-- Name: support_messages; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.support_messages (
    id integer NOT NULL,
    ticket_id integer NOT NULL,
    sender_id bigint NOT NULL,
    message text NOT NULL,
    is_admin_reply boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.support_messages OWNER TO neondb_owner;

--
-- Name: support_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.support_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.support_messages_id_seq OWNER TO neondb_owner;

--
-- Name: support_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.support_messages_id_seq OWNED BY public.support_messages.id;


--
-- Name: support_tickets; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.support_tickets (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    subject character varying(255) NOT NULL,
    description text,
    status character varying(20) NOT NULL,
    priority character varying(10) NOT NULL,
    category character varying(50),
    assigned_to bigint,
    admin_notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    resolved_at timestamp with time zone,
    ticket_id character varying(20)
);


ALTER TABLE public.support_tickets OWNER TO neondb_owner;

--
-- Name: support_tickets_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.support_tickets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.support_tickets_id_seq OWNER TO neondb_owner;

--
-- Name: support_tickets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.support_tickets_id_seq OWNED BY public.support_tickets.id;


--
-- Name: system_config; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.system_config (
    key character varying(100) NOT NULL,
    value text NOT NULL,
    value_type character varying(20) NOT NULL,
    description text,
    is_public boolean NOT NULL,
    is_encrypted boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_by bigint
);


ALTER TABLE public.system_config OWNER TO neondb_owner;

--
-- Name: transaction_engine_events; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.transaction_engine_events (
    id integer NOT NULL,
    event_id character varying(50) NOT NULL,
    transaction_id integer NOT NULL,
    saga_id character varying(50),
    event_type character varying(50) NOT NULL,
    event_category character varying(20) NOT NULL,
    event_data jsonb NOT NULL,
    previous_state jsonb,
    new_state jsonb,
    triggered_by character varying(50) NOT NULL,
    user_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.transaction_engine_events OWNER TO neondb_owner;

--
-- Name: transaction_engine_events_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.transaction_engine_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transaction_engine_events_id_seq OWNER TO neondb_owner;

--
-- Name: transaction_engine_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.transaction_engine_events_id_seq OWNED BY public.transaction_engine_events.id;


--
-- Name: transactions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.transactions (
    id integer NOT NULL,
    transaction_id character varying(36) NOT NULL,
    user_id bigint NOT NULL,
    transaction_type character varying(50) NOT NULL,
    amount numeric(38,18) NOT NULL,
    currency character varying(10) NOT NULL,
    fee numeric(38,18),
    status character varying(20) NOT NULL,
    provider character varying(20),
    external_id character varying(100),
    external_tx_id character varying(100),
    blockchain_tx_hash character varying(100),
    escrow_id integer,
    cashout_id integer,
    description text,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone,
    confirmed_at timestamp with time zone,
    utid character varying(32),
    CONSTRAINT ck_transaction_amount_positive CHECK ((amount > (0)::numeric)),
    CONSTRAINT ck_transaction_entity_link_required CHECK (((((transaction_type)::text = ANY (ARRAY[('escrow_payment'::character varying)::text, ('escrow_release'::character varying)::text, ('escrow_refund'::character varying)::text, ('escrow_overpayment'::character varying)::text])) AND (escrow_id IS NOT NULL)) OR (((transaction_type)::text = ANY (ARRAY[('cashout'::character varying)::text, ('cashout_hold'::character varying)::text, ('cashout_hold_release'::character varying)::text])) AND (cashout_id IS NOT NULL)) OR ((transaction_type)::text = ANY (ARRAY[('deposit'::character varying)::text, ('withdrawal'::character varying)::text, ('wallet_transfer'::character varying)::text, ('wallet_deposit'::character varying)::text, ('wallet_payment'::character varying)::text, ('fee'::character varying)::text, ('admin_adjustment'::character varying)::text, ('referral_welcome_bonus'::character varying)::text])))),
    CONSTRAINT ck_transaction_status_valid CHECK (((status)::text = ANY (ARRAY[('pending'::character varying)::text, ('confirmed'::character varying)::text, ('completed'::character varying)::text, ('failed'::character varying)::text, ('cancelled'::character varying)::text]))),
    CONSTRAINT ck_transaction_type_valid CHECK (((transaction_type)::text = ANY (ARRAY[('deposit'::character varying)::text, ('withdrawal'::character varying)::text, ('escrow_payment'::character varying)::text, ('escrow_release'::character varying)::text, ('escrow_refund'::character varying)::text, ('escrow_overpayment'::character varying)::text, ('wallet_transfer'::character varying)::text, ('wallet_deposit'::character varying)::text, ('wallet_payment'::character varying)::text, ('cashout'::character varying)::text, ('cashout_hold'::character varying)::text, ('cashout_hold_release'::character varying)::text, ('fee'::character varying)::text, ('admin_adjustment'::character varying)::text, ('referral_welcome_bonus'::character varying)::text])))
);


ALTER TABLE public.transactions OWNER TO neondb_owner;

--
-- Name: transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transactions_id_seq OWNER TO neondb_owner;

--
-- Name: transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.transactions_id_seq OWNED BY public.transactions.id;


--
-- Name: unified_transaction_retry_logs; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.unified_transaction_retry_logs (
    id integer NOT NULL,
    transaction_id integer NOT NULL,
    retry_attempt integer NOT NULL,
    retry_reason character varying(100) NOT NULL,
    error_code character varying(50) NOT NULL,
    error_message text,
    error_details jsonb,
    retry_strategy character varying(50) NOT NULL,
    delay_seconds integer NOT NULL,
    next_retry_at timestamp without time zone,
    external_provider character varying(50),
    external_response_code character varying(20),
    external_response_body text,
    retry_successful boolean,
    final_retry boolean NOT NULL,
    attempted_at timestamp without time zone NOT NULL,
    completed_at timestamp without time zone,
    duration_ms integer
);


ALTER TABLE public.unified_transaction_retry_logs OWNER TO neondb_owner;

--
-- Name: unified_transaction_retry_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.unified_transaction_retry_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.unified_transaction_retry_logs_id_seq OWNER TO neondb_owner;

--
-- Name: unified_transaction_retry_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.unified_transaction_retry_logs_id_seq OWNED BY public.unified_transaction_retry_logs.id;


--
-- Name: unified_transaction_status_history; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.unified_transaction_status_history (
    id integer NOT NULL,
    transaction_id integer NOT NULL,
    from_status character varying(20),
    to_status character varying(20) NOT NULL,
    change_reason character varying(100) NOT NULL,
    changed_by bigint,
    system_action boolean NOT NULL,
    changed_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.unified_transaction_status_history OWNER TO neondb_owner;

--
-- Name: unified_transaction_status_history_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.unified_transaction_status_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.unified_transaction_status_history_id_seq OWNER TO neondb_owner;

--
-- Name: unified_transaction_status_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.unified_transaction_status_history_id_seq OWNED BY public.unified_transaction_status_history.id;


--
-- Name: unified_transactions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.unified_transactions (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    transaction_type character varying(25) NOT NULL,
    status character varying(20) NOT NULL,
    amount numeric(38,18) NOT NULL,
    currency character varying(10) NOT NULL,
    fee numeric(38,18),
    phase character varying(20),
    external_id character varying(255),
    reference_id character varying(255),
    metadata jsonb,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    description text
);


ALTER TABLE public.unified_transactions OWNER TO neondb_owner;

--
-- Name: unified_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.unified_transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.unified_transactions_id_seq OWNER TO neondb_owner;

--
-- Name: unified_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.unified_transactions_id_seq OWNED BY public.unified_transactions.id;


--
-- Name: user_achievements; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.user_achievements (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    achievement_type character varying(50) NOT NULL,
    achievement_name character varying(200) NOT NULL,
    achievement_description text,
    achievement_tier integer NOT NULL,
    target_value numeric(20,2) NOT NULL,
    current_value numeric(20,2) NOT NULL,
    achieved boolean NOT NULL,
    reward_message text,
    badge_emoji character varying(50),
    points_awarded integer NOT NULL,
    first_eligible_at timestamp with time zone,
    achieved_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    trigger_transaction_id integer,
    trigger_escrow_id character varying(20),
    additional_context json
);


ALTER TABLE public.user_achievements OWNER TO neondb_owner;

--
-- Name: user_achievements_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.user_achievements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_achievements_id_seq OWNER TO neondb_owner;

--
-- Name: user_achievements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.user_achievements_id_seq OWNED BY public.user_achievements.id;


--
-- Name: user_contacts; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.user_contacts (
    id integer NOT NULL,
    contact_id character varying(50) NOT NULL,
    user_id bigint NOT NULL,
    contact_type character varying(20) NOT NULL,
    contact_value character varying(255) NOT NULL,
    is_verified boolean NOT NULL,
    verified_at timestamp without time zone,
    verification_code character varying(10),
    verification_expires timestamp without time zone,
    verification_attempts integer NOT NULL,
    is_primary boolean NOT NULL,
    last_used timestamp without time zone,
    is_active boolean NOT NULL,
    notifications_enabled boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.user_contacts OWNER TO neondb_owner;

--
-- Name: user_contacts_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.user_contacts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_contacts_id_seq OWNER TO neondb_owner;

--
-- Name: user_contacts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.user_contacts_id_seq OWNED BY public.user_contacts.id;


--
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.user_sessions (
    session_id character varying(100) NOT NULL,
    user_id bigint NOT NULL,
    session_type character varying(50) NOT NULL,
    status character varying(20) NOT NULL,
    data jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    last_accessed timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.user_sessions OWNER TO neondb_owner;

--
-- Name: user_sms_usage; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.user_sms_usage (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    date date NOT NULL,
    sms_count integer NOT NULL,
    last_sms_sent_at timestamp without time zone,
    phone_numbers_contacted text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.user_sms_usage OWNER TO neondb_owner;

--
-- Name: user_sms_usage_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.user_sms_usage_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_sms_usage_id_seq OWNER TO neondb_owner;

--
-- Name: user_sms_usage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.user_sms_usage_id_seq OWNED BY public.user_sms_usage.id;


--
-- Name: user_streak_tracking; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.user_streak_tracking (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    daily_activity_streak integer NOT NULL,
    best_daily_activity_streak integer NOT NULL,
    activity_reset_count integer NOT NULL,
    last_activity_date timestamp with time zone,
    successful_trades_streak integer NOT NULL,
    best_successful_trades_streak integer NOT NULL,
    successful_trades_reset_count integer NOT NULL,
    last_successful_trade_date timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.user_streak_tracking OWNER TO neondb_owner;

--
-- Name: user_streak_tracking_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.user_streak_tracking_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_streak_tracking_id_seq OWNER TO neondb_owner;

--
-- Name: user_streak_tracking_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.user_streak_tracking_id_seq OWNED BY public.user_streak_tracking.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.users (
    id bigint NOT NULL,
    telegram_id bigint NOT NULL,
    username character varying(32),
    first_name character varying(64),
    last_name character varying(64),
    phone_number character varying(20),
    email character varying(255),
    email_verified boolean NOT NULL,
    language_code character varying(10),
    timezone character varying(50),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    last_activity timestamp without time zone,
    is_active boolean NOT NULL,
    is_verified boolean NOT NULL,
    is_blocked boolean NOT NULL,
    is_admin boolean NOT NULL,
    is_seller boolean NOT NULL,
    auto_cashout_enabled boolean NOT NULL,
    auto_cashout_crypto_address_id integer,
    auto_cashout_bank_account_id integer,
    status character varying(50),
    conversation_state character varying(100),
    terms_accepted_at timestamp with time zone,
    onboarded_at timestamp with time zone,
    onboarding_completed boolean NOT NULL,
    referral_code character varying(20),
    referred_by_id bigint,
    total_referrals integer NOT NULL,
    referral_earnings numeric(20,8) NOT NULL,
    reputation_score integer NOT NULL,
    completed_trades integer NOT NULL,
    successful_trades integer NOT NULL,
    failed_trades integer NOT NULL,
    avg_rating numeric(3,2) NOT NULL,
    total_ratings integer NOT NULL,
    profile_image_url character varying(255),
    bio text,
    cashout_preference character varying(20),
    universal_welcome_bonus_given boolean DEFAULT false NOT NULL,
    universal_welcome_bonus_given_at timestamp with time zone,
    profile_slug character varying(50)
);


ALTER TABLE public.users OWNER TO neondb_owner;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO neondb_owner;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: wallet_balance_snapshots; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.wallet_balance_snapshots (
    id integer NOT NULL,
    snapshot_id character varying(100) NOT NULL,
    wallet_type character varying(20) NOT NULL,
    user_id bigint,
    wallet_id integer,
    internal_wallet_id character varying(100),
    currency character varying(10) NOT NULL,
    available_balance numeric(20,8) NOT NULL,
    frozen_balance numeric(20,8) NOT NULL,
    locked_balance numeric(20,8) NOT NULL,
    reserved_balance numeric(20,8) NOT NULL,
    total_balance numeric(20,8) NOT NULL,
    snapshot_type character varying(50) NOT NULL,
    trigger_event character varying(100),
    previous_snapshot_id character varying(100),
    balance_checksum character varying(64) NOT NULL,
    transaction_count integer NOT NULL,
    last_transaction_id character varying(100),
    validation_passed boolean NOT NULL,
    validation_errors text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    valid_from timestamp with time zone NOT NULL,
    valid_until timestamp with time zone,
    created_by character varying(50) NOT NULL,
    hostname character varying(100),
    process_id character varying(50),
    snapshot_metadata text,
    notes text,
    CONSTRAINT chk_positive_total_balance CHECK ((total_balance >= (0)::numeric)),
    CONSTRAINT chk_snapshot_valid_wallet_type CHECK (((wallet_type)::text = ANY (ARRAY[('user'::character varying)::text, ('internal'::character varying)::text])))
);


ALTER TABLE public.wallet_balance_snapshots OWNER TO neondb_owner;

--
-- Name: wallet_balance_snapshots_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.wallet_balance_snapshots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.wallet_balance_snapshots_id_seq OWNER TO neondb_owner;

--
-- Name: wallet_balance_snapshots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.wallet_balance_snapshots_id_seq OWNED BY public.wallet_balance_snapshots.id;


--
-- Name: wallet_holds; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.wallet_holds (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    currency character varying(10) NOT NULL,
    amount numeric(38,18) NOT NULL,
    hold_type character varying(50) NOT NULL,
    reference_id character varying(100) NOT NULL,
    status character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone,
    released_at timestamp with time zone
);


ALTER TABLE public.wallet_holds OWNER TO neondb_owner;

--
-- Name: wallet_holds_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.wallet_holds_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.wallet_holds_id_seq OWNER TO neondb_owner;

--
-- Name: wallet_holds_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.wallet_holds_id_seq OWNED BY public.wallet_holds.id;


--
-- Name: wallets; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.wallets (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    currency character varying(10) NOT NULL,
    available_balance numeric(38,18) NOT NULL,
    frozen_balance numeric(38,18) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    utid character varying(32),
    trading_credit numeric(38,18) DEFAULT 0 NOT NULL,
    CONSTRAINT ck_wallet_available_positive CHECK ((available_balance >= (0)::numeric)),
    CONSTRAINT ck_wallet_frozen_positive CHECK ((frozen_balance >= (0)::numeric)),
    CONSTRAINT ck_wallet_trading_credit_positive CHECK ((trading_credit >= (0)::numeric))
);


ALTER TABLE public.wallets OWNER TO neondb_owner;

--
-- Name: wallets_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.wallets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.wallets_id_seq OWNER TO neondb_owner;

--
-- Name: wallets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.wallets_id_seq OWNED BY public.wallets.id;


--
-- Name: webhook_event_ledger; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.webhook_event_ledger (
    id integer NOT NULL,
    event_provider character varying(50) NOT NULL,
    event_id character varying(255) NOT NULL,
    event_type character varying(50) NOT NULL,
    payload jsonb NOT NULL,
    txid character varying(255),
    reference_id character varying(255),
    status character varying(50) NOT NULL,
    amount numeric(38,18),
    currency character varying(10),
    processed_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    webhook_payload text,
    processing_result text,
    error_message text,
    retry_count integer NOT NULL,
    user_id bigint,
    event_metadata json,
    processing_duration_ms integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.webhook_event_ledger OWNER TO neondb_owner;

--
-- Name: webhook_event_ledger_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.webhook_event_ledger_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.webhook_event_ledger_id_seq OWNER TO neondb_owner;

--
-- Name: webhook_event_ledger_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.webhook_event_ledger_id_seq OWNED BY public.webhook_event_ledger.id;


--
-- Name: replit_database_migrations_v1 id; Type: DEFAULT; Schema: _system; Owner: neondb_owner
--

ALTER TABLE ONLY _system.replit_database_migrations_v1 ALTER COLUMN id SET DEFAULT nextval('_system.replit_database_migrations_v1_id_seq'::regclass);


--
-- Name: admin_action_tokens id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.admin_action_tokens ALTER COLUMN id SET DEFAULT nextval('public.admin_action_tokens_id_seq'::regclass);


--
-- Name: admin_operation_overrides id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.admin_operation_overrides ALTER COLUMN id SET DEFAULT nextval('public.admin_operation_overrides_id_seq'::regclass);


--
-- Name: audit_events id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.audit_events ALTER COLUMN id SET DEFAULT nextval('public.audit_events_id_seq'::regclass);


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: balance_alert_state id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.balance_alert_state ALTER COLUMN id SET DEFAULT nextval('public.balance_alert_state_id_seq'::regclass);


--
-- Name: balance_audit_logs id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.balance_audit_logs ALTER COLUMN id SET DEFAULT nextval('public.balance_audit_logs_id_seq'::regclass);


--
-- Name: balance_protection_logs id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.balance_protection_logs ALTER COLUMN id SET DEFAULT nextval('public.balance_protection_logs_id_seq'::regclass);


--
-- Name: balance_reconciliation_logs id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.balance_reconciliation_logs ALTER COLUMN id SET DEFAULT nextval('public.balance_reconciliation_logs_id_seq'::regclass);


--
-- Name: cashouts id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.cashouts ALTER COLUMN id SET DEFAULT nextval('public.cashouts_id_seq'::regclass);


--
-- Name: crypto_deposits id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.crypto_deposits ALTER COLUMN id SET DEFAULT nextval('public.crypto_deposits_id_seq'::regclass);


--
-- Name: dispute_messages id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.dispute_messages ALTER COLUMN id SET DEFAULT nextval('public.dispute_messages_id_seq'::regclass);


--
-- Name: disputes id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.disputes ALTER COLUMN id SET DEFAULT nextval('public.disputes_id_seq'::regclass);


--
-- Name: distributed_locks id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.distributed_locks ALTER COLUMN id SET DEFAULT nextval('public.distributed_locks_id_seq'::regclass);


--
-- Name: email_verifications id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.email_verifications ALTER COLUMN id SET DEFAULT nextval('public.email_verifications_id_seq'::regclass);


--
-- Name: escrow_holdings id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrow_holdings ALTER COLUMN id SET DEFAULT nextval('public.escrow_holdings_id_seq'::regclass);


--
-- Name: escrow_messages id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrow_messages ALTER COLUMN id SET DEFAULT nextval('public.escrow_messages_id_seq'::regclass);


--
-- Name: escrow_refund_operations id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrow_refund_operations ALTER COLUMN id SET DEFAULT nextval('public.escrow_refund_operations_id_seq'::regclass);


--
-- Name: escrows id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrows ALTER COLUMN id SET DEFAULT nextval('public.escrows_id_seq'::regclass);


--
-- Name: exchange_orders id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.exchange_orders ALTER COLUMN id SET DEFAULT nextval('public.exchange_orders_id_seq'::regclass);


--
-- Name: idempotency_keys id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.idempotency_keys ALTER COLUMN id SET DEFAULT nextval('public.idempotency_keys_id_seq'::regclass);


--
-- Name: idempotency_tokens id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.idempotency_tokens ALTER COLUMN id SET DEFAULT nextval('public.idempotency_tokens_id_seq'::regclass);


--
-- Name: inbox_webhooks id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.inbox_webhooks ALTER COLUMN id SET DEFAULT nextval('public.inbox_webhooks_id_seq'::regclass);


--
-- Name: internal_wallets id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.internal_wallets ALTER COLUMN id SET DEFAULT nextval('public.internal_wallets_id_seq'::regclass);


--
-- Name: notification_activities id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.notification_activities ALTER COLUMN id SET DEFAULT nextval('public.notification_activities_id_seq'::regclass);


--
-- Name: notification_preferences id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.notification_preferences ALTER COLUMN id SET DEFAULT nextval('public.notification_preferences_id_seq'::regclass);


--
-- Name: notification_queue id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.notification_queue ALTER COLUMN id SET DEFAULT nextval('public.notification_queue_id_seq'::regclass);


--
-- Name: onboarding_sessions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.onboarding_sessions ALTER COLUMN id SET DEFAULT nextval('public.onboarding_sessions_id_seq'::regclass);


--
-- Name: otp_verifications id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.otp_verifications ALTER COLUMN id SET DEFAULT nextval('public.otp_verifications_id_seq'::regclass);


--
-- Name: outbox_events id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.outbox_events ALTER COLUMN id SET DEFAULT nextval('public.outbox_events_id_seq'::regclass);


--
-- Name: payment_addresses id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.payment_addresses ALTER COLUMN id SET DEFAULT nextval('public.payment_addresses_id_seq'::regclass);


--
-- Name: pending_cashouts id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pending_cashouts ALTER COLUMN id SET DEFAULT nextval('public.pending_cashouts_id_seq'::regclass);


--
-- Name: platform_revenue id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.platform_revenue ALTER COLUMN id SET DEFAULT nextval('public.platform_revenue_id_seq'::regclass);


--
-- Name: ratings id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ratings ALTER COLUMN id SET DEFAULT nextval('public.ratings_id_seq'::regclass);


--
-- Name: refunds id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.refunds ALTER COLUMN id SET DEFAULT nextval('public.refunds_id_seq'::regclass);


--
-- Name: saga_steps id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.saga_steps ALTER COLUMN id SET DEFAULT nextval('public.saga_steps_id_seq'::regclass);


--
-- Name: saved_addresses id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.saved_addresses ALTER COLUMN id SET DEFAULT nextval('public.saved_addresses_id_seq'::regclass);


--
-- Name: saved_bank_accounts id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.saved_bank_accounts ALTER COLUMN id SET DEFAULT nextval('public.saved_bank_accounts_id_seq'::regclass);


--
-- Name: security_audits id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.security_audits ALTER COLUMN id SET DEFAULT nextval('public.security_audits_id_seq'::regclass);


--
-- Name: support_messages id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.support_messages ALTER COLUMN id SET DEFAULT nextval('public.support_messages_id_seq'::regclass);


--
-- Name: support_tickets id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.support_tickets ALTER COLUMN id SET DEFAULT nextval('public.support_tickets_id_seq'::regclass);


--
-- Name: transaction_engine_events id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.transaction_engine_events ALTER COLUMN id SET DEFAULT nextval('public.transaction_engine_events_id_seq'::regclass);


--
-- Name: transactions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.transactions ALTER COLUMN id SET DEFAULT nextval('public.transactions_id_seq'::regclass);


--
-- Name: unified_transaction_retry_logs id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.unified_transaction_retry_logs ALTER COLUMN id SET DEFAULT nextval('public.unified_transaction_retry_logs_id_seq'::regclass);


--
-- Name: unified_transaction_status_history id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.unified_transaction_status_history ALTER COLUMN id SET DEFAULT nextval('public.unified_transaction_status_history_id_seq'::regclass);


--
-- Name: unified_transactions id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.unified_transactions ALTER COLUMN id SET DEFAULT nextval('public.unified_transactions_id_seq'::regclass);


--
-- Name: user_achievements id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_achievements ALTER COLUMN id SET DEFAULT nextval('public.user_achievements_id_seq'::regclass);


--
-- Name: user_contacts id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_contacts ALTER COLUMN id SET DEFAULT nextval('public.user_contacts_id_seq'::regclass);


--
-- Name: user_sms_usage id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_sms_usage ALTER COLUMN id SET DEFAULT nextval('public.user_sms_usage_id_seq'::regclass);


--
-- Name: user_streak_tracking id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_streak_tracking ALTER COLUMN id SET DEFAULT nextval('public.user_streak_tracking_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: wallet_balance_snapshots id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallet_balance_snapshots ALTER COLUMN id SET DEFAULT nextval('public.wallet_balance_snapshots_id_seq'::regclass);


--
-- Name: wallet_holds id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallet_holds ALTER COLUMN id SET DEFAULT nextval('public.wallet_holds_id_seq'::regclass);


--
-- Name: wallets id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallets ALTER COLUMN id SET DEFAULT nextval('public.wallets_id_seq'::regclass);


--
-- Name: webhook_event_ledger id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.webhook_event_ledger ALTER COLUMN id SET DEFAULT nextval('public.webhook_event_ledger_id_seq'::regclass);


--
-- Data for Name: replit_database_migrations_v1; Type: TABLE DATA; Schema: _system; Owner: neondb_owner
--

COPY _system.replit_database_migrations_v1 (id, build_id, deployment_id, statement_count, applied_at) FROM stdin;
1	7132620c-20a3-4366-a01b-4d16742fc469	c9e2bc7c-6253-464e-a7b8-6f4c69a5cec0	1	2025-10-18 09:15:56.497325+00
2	00297811-6f3b-4a7e-a851-2409f21f55be	c9e2bc7c-6253-464e-a7b8-6f4c69a5cec0	1	2025-10-18 11:26:47.84103+00
\.


--
-- Data for Name: admin_action_tokens; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.admin_action_tokens (id, token, action, cashout_id, admin_email, admin_user_id, created_at, expires_at, used_at, used_by_ip, used_by_user_agent, action_result, error_message, completed_at) FROM stdin;
\.


--
-- Data for Name: admin_operation_overrides; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.admin_operation_overrides (id, provider, operation_type, override_type, reason, created_by, is_active, expires_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: audit_events; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.audit_events (id, event_id, event_type, entity_type, entity_id, event_data, user_id, processed, processed_at, created_at) FROM stdin;
1	d16a9ff5-0b5c-49fb-b528-c1bc11ea75e0	wallet_deposit_address_generated	wallet	wallet_5590563715	{"amount": "1.0", "currency": "ETH", "failover_used": true, "address_prefix": "0xbb87ae5d", "payment_provider": "dynopay", "qr_code_available": true, "wallet_transaction_id": "WALLET-***563715"}	5590563715	f	\N	2025-10-18 08:08:34.441011+00
2	c8c99adb-b919-45c0-968c-5c94dc9444f3	wallet_deposit_address_generated	wallet	wallet_5590563715	{"amount": "1.0", "currency": "ETH", "failover_used": true, "address_prefix": "0x74ba9359", "payment_provider": "dynopay", "qr_code_available": true, "wallet_transaction_id": "WALLET-***563715"}	5590563715	f	\N	2025-10-18 09:23:17.188163+00
3	eae51c89-e532-4e96-b49f-49f4af6343da	wallet_deposit_address_generated	wallet	wallet_5590563715	{"amount": "1.0", "currency": "ETH", "failover_used": true, "address_prefix": "0x372a3513", "payment_provider": "dynopay", "qr_code_available": true, "wallet_transaction_id": "WALLET-***563715"}	5590563715	f	\N	2025-10-18 09:31:02.063531+00
4	5b0b730d-9ff1-48cd-b571-16e0f0ce7b18	wallet_deposit_address_generated	wallet	wallet_5590563715	{"amount": "1.0", "currency": "ETH", "failover_used": true, "address_prefix": "0x387ae2db", "payment_provider": "dynopay", "qr_code_available": true, "wallet_transaction_id": "WALLET-***563715"}	5590563715	f	\N	2025-10-18 09:39:51.414938+00
5	aa610625-835d-450f-8138-608508eb4e22	webhook_event_recorded	webhook_event	de7ba9b8-8fcf-4e67-8aaf-24c0ebc0617b	{"txid": "de7ba9b8-8fcf-4e67-8aaf-24c0ebc0617b", "amount": "0.008800", "source": "webhook_idempotency_service.record_webhook_event", "currency": "ETH", "reference_id": "ES101825T98K"}	\N	f	\N	2025-10-18 09:44:20.208778+00
6	b64a2cb7-a16b-466e-bf01-ba4fecd27696	webhook_status_updated	webhook_event	de7ba9b8-8fcf-4e67-8aaf-24c0ebc0617b	{"txid": "de7ba9b8-8fcf-4e67-8aaf-24c0ebc0617b", "amount": "0.008800000000000000", "source": "webhook_idempotency_service.update_processing_status", "currency": "ETH", "has_error": false, "retry_count": 0, "reference_id": "ES101825T98K"}	\N	f	\N	2025-10-18 09:44:29.171899+00
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.audit_logs (id, event_type, entity_type, entity_id, user_id, admin_id, previous_state, new_state, changes, description, ip_address, user_agent, extra_data, created_at) FROM stdin;
\.


--
-- Data for Name: balance_alert_state; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.balance_alert_state (id, alert_key, provider, currency, alert_level, last_alert_time, alert_count, created_at, updated_at) FROM stdin;
1	kraken_USD_WARNING	kraken	USD	WARNING	2025-10-18 03:28:28.212707+00	1	2025-10-18 03:28:28.212707+00	2025-10-18 03:28:28.212707+00
\.


--
-- Data for Name: balance_audit_logs; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.balance_audit_logs (id, audit_id, wallet_type, user_id, wallet_id, internal_wallet_id, currency, balance_type, amount_before, amount_after, change_amount, change_type, transaction_id, transaction_type, operation_type, initiated_by, initiated_by_id, reason, escrow_pk, escrow_id, cashout_id, exchange_id, balance_validation_passed, pre_validation_checksum, post_validation_checksum, idempotency_key, created_at, processed_at, audit_metadata, ip_address, user_agent, api_version, hostname, process_id, thread_id) FROM stdin;
\.


--
-- Data for Name: balance_protection_logs; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.balance_protection_logs (id, operation_type, currency, amount, user_id, operation_allowed, alert_level, balance_check_passed, insufficient_services, warning_message, blocking_reason, fincra_balance, kraken_balances, created_at) FROM stdin;
\.


--
-- Data for Name: balance_reconciliation_logs; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.balance_reconciliation_logs (id, reconciliation_id, reconciliation_type, target_type, user_id, internal_wallet_id, currency, status, discrepancies_found, discrepancies_resolved, total_amount_discrepancy, wallets_checked, transactions_verified, snapshots_created, audit_logs_created, started_at, completed_at, duration_seconds, triggered_by, triggered_by_id, trigger_reason, findings_summary, actions_taken, recommendations, error_count, last_error_message, warning_count, hostname, process_id, version, configuration, reconciliation_metadata, notes) FROM stdin;
\.


--
-- Data for Name: cashouts; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.cashouts (id, cashout_id, user_id, amount, currency, cashout_type, destination_type, destination_address, bank_details, network_fee, platform_fee, net_amount, pricing_snapshot, status, provider, external_id, external_reference, admin_approved, admin_notes, created_at, processed_at, completed_at, error_message, retry_count, utid, destination, bank_account_id, cashout_metadata, external_tx_id, fincra_request_id, processing_mode, failure_type, last_error_code, failed_at, technical_failure_since) FROM stdin;
\.


--
-- Data for Name: crypto_deposits; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.crypto_deposits (id, provider, txid, order_id, address_in, address_out, coin, amount, amount_fiat, confirmations, required_confirmations, status, user_id, created_at, confirmed_at, credited_at) FROM stdin;
1	dynopay	ffdb60e9-150e-40a2-9c6c-3d21bcb97faf	WALLET-20251018-093059-5590563715	dynopay_wallet_deposit	\N	ETH	0.00580000	22.51496200	1	1	credited	5590563715	2025-10-18 09:32:45.530836	\N	\N
2	dynopay	a6a507b6-a533-4807-b042-d770f5f6ca91	WALLET-20251018-093949-5590563715	dynopay_wallet_deposit	\N	ETH	0.00380000	14.73928800	1	1	credited	5590563715	2025-10-18 09:41:20.91415	\N	\N
\.


--
-- Data for Name: dispute_messages; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.dispute_messages (id, dispute_id, sender_id, message, created_at) FROM stdin;
\.


--
-- Data for Name: disputes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.disputes (id, escrow_id, initiator_id, respondent_id, dispute_type, reason, status, admin_assigned_id, resolution, resolved_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: distributed_locks; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.distributed_locks (id, lock_name, locked_by, locked_at, expires_at, metadata) FROM stdin;
\.


--
-- Data for Name: email_verifications; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.email_verifications (id, user_id, email, verification_code, purpose, verified, attempts, max_attempts, created_at, expires_at, verified_at, deleted_at) FROM stdin;
1	5590563715	onarrival21@gmail.com	591352	registration	t	1	5	2025-10-18 03:40:56.334127+00	2025-10-18 03:55:56.334127+00	2025-10-18 03:41:18.690519+00	\N
3	5168006768	cloakhost@tutamail.com	385976	registration	t	1	5	2025-10-18 03:42:37.839577+00	2025-10-18 03:57:37.92146+00	2025-10-18 03:42:58.358323+00	\N
4	6810331325	cameronwilson89@protonmail.com	733522	registration	t	1	5	2025-10-18 05:19:00.107581+00	2025-10-18 05:34:00.184187+00	2025-10-18 05:19:31.561614+00	\N
5	7448028858	qwfawfwafwq@redgre.com	483917	registration	f	0	5	2025-10-18 05:57:21.580301+00	2025-10-18 06:12:21.663379+00	\N	\N
6	7289467354	Meganbaxter696@gmail.com	633375	registration	t	1	5	2025-10-18 07:13:16.843203+00	2025-10-18 07:28:17.149727+00	2025-10-18 07:14:01.497437+00	\N
\.


--
-- Data for Name: escrow_holdings; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.escrow_holdings (id, escrow_id, amount_held, currency, overpayment_amount, overpayment_currency, overpayment_usd_value, overpayment_transaction_id, original_amount, total_released, remaining_amount, partial_releases_count, created_at, released_at, first_release_at, released_to_user_id, status) FROM stdin;
1	ES101825T98K	34.14224000	USD	\N	\N	\N	\N	\N	0.00000000	\N	0	2025-10-18 09:44:23.57903	\N	\N	\N	active
\.


--
-- Data for Name: escrow_messages; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.escrow_messages (id, escrow_id, sender_id, content, message_type, attachments, created_at) FROM stdin;
1	1	5168006768	Join	text	\N	2025-10-18 09:44:54.97694
\.


--
-- Data for Name: escrow_refund_operations; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.escrow_refund_operations (id, escrow_id, buyer_id, refund_cycle_id, refund_reason, amount_refunded, currency, transaction_id, idempotency_key, processed_by_service, processing_context, status, created_at) FROM stdin;
\.


--
-- Data for Name: escrows; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.escrows (id, escrow_id, utid, buyer_id, seller_id, seller_email, seller_contact_type, seller_contact_value, seller_contact_display, amount, currency, fee_amount, total_amount, pricing_snapshot, description, payment_method, deposit_address, deposit_tx_hash, status, expires_at, created_at, updated_at, payment_confirmed_at, completed_at, delivery_deadline, auto_release_at, admin_notes, dispute_reason, fee_split_option, buyer_fee_amount, seller_fee_amount, seller_accepted_at, delivered_at, warning_24h_sent, warning_8h_sent, warning_2h_sent, warning_30m_sent) FROM stdin;
1	ES101825T98K	ES101825T98K	5590563715	5168006768	\N	username	hostbay_support	@hostbay_support	30.000000000000000000	USD	0.000000000000000000	30.000000000000000000	{"delivery_hours": 24}	Buying goods	crypto_ETH	0x817ab4dde766a4bd85f425e577ec07066966ea22	de7ba9b8-8fcf-4e67-8aaf-24c0ebc0617b	active	2025-10-19 09:44:20.921009+00	2025-10-18 09:42:16.740815+00	2025-10-18 09:42:16.293828	2025-10-18 09:44:20.921009+00	\N	2025-10-19 09:44:20.921009+00	2025-10-20 09:44:20.921009+00	\N	\N	buyer_pays	0.000000000000000000	0.000000000000000000	2025-10-18 09:44:42.197031+00	\N	t	f	f	f
\.


--
-- Data for Name: exchange_orders; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.exchange_orders (id, utid, exchange_id, user_id, order_type, source_currency, source_amount, source_network, target_currency, target_amount, target_network, exchange_rate, markup_percentage, fee_amount, final_amount, usd_equivalent, rate_locked_at, rate_lock_expires_at, rate_lock_duration_minutes, crypto_address, bank_account, wallet_address, deposit_tx_hash, payout_tx_hash, bank_reference, status, provider, created_at, updated_at, completed_at, expires_at) FROM stdin;
\.


--
-- Data for Name: idempotency_keys; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.idempotency_keys (id, operation_key, user_id, operation_type, entity_id, result_data, success, error_message, created_at, expires_at) FROM stdin;
1	crypto_payment_ES101825T98K	5590563715	escrow_create	ES101825T98K	{"escrow_id": "ES101825T98K", "escrow_utid": "ES101825T98K"}	t	\N	2025-10-18 09:42:16.293828+00	2025-10-19 09:42:16.486066+00
\.


--
-- Data for Name: idempotency_tokens; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.idempotency_tokens (id, idempotency_key, operation_type, resource_id, status, result_data, error_message, created_at, completed_at, expires_at, metadata_json) FROM stdin;
\.


--
-- Data for Name: inbox_webhooks; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.inbox_webhooks (id, webhook_id, provider, event_type, status, raw_payload, processed_data, transaction_id, user_id, first_received_at, processed_at, retry_count, last_error, error_details) FROM stdin;
\.


--
-- Data for Name: internal_wallets; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.internal_wallets (id, wallet_id, provider_name, currency, provider_account_id, available_balance, locked_balance, reserved_balance, total_balance, minimum_balance, withdrawal_limit, daily_limit, is_active, auto_reconcile, emergency_freeze, created_at, updated_at, last_reconciled_at, last_balance_check_at, version, configuration, notes) FROM stdin;
\.


--
-- Data for Name: notification_activities; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.notification_activities (id, activity_id, user_id, notification_type, channel_type, channel_value, sent_at, delivered_at, opened_at, clicked_at, response_time, delivery_status, engagement_level, priority_score, device_type, location_context, created_at, idempotency_key) FROM stdin;
1	activity_5168006768_1760758984_telegram	5168006768	payments	telegram	5168006768	2025-10-18 03:43:04.938581	2025-10-18 03:43:04.549478	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 03:43:05.173886	\N
2	activity_5168006768_1760758984_email	5168006768	payments	email	cloakhost@tutamail.com	2025-10-18 03:43:04.9388	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 03:43:05.173886	\N
3	activity_5168006768_1760758986_telegram	5168006768	payments	telegram	5168006768	2025-10-18 03:43:06.239557	2025-10-18 03:43:06.236431	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 03:43:06.456951	\N
4	activity_5168006768_1760758987_email	5168006768	payments	email	cloakhost@tutamail.com	2025-10-18 03:43:07.996364	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 03:43:08.219106	\N
5	activity_5590563715_1760758989_telegram	5590563715	payments	telegram	5590563715	2025-10-18 03:43:09.627867	2025-10-18 03:43:09.625189	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 03:43:09.837768	\N
6	activity_5590563715_1760758990_email	5590563715	payments	email	onarrival21@gmail.com	2025-10-18 03:43:10.892021	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 03:43:11.115976	\N
7	activity_6810331325_1760764789_telegram	6810331325	payments	telegram	6810331325	2025-10-18 05:19:49.524374	2025-10-18 05:19:49.035791	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 05:19:49.744216	\N
8	activity_6810331325_1760764789_email	6810331325	payments	email	cameronwilson89@protonmail.com	2025-10-18 05:19:49.524577	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 05:19:49.744216	\N
9	activity_6810331325_1760764806_telegram	6810331325	payments	telegram	6810331325	2025-10-18 05:20:06.261937	2025-10-18 05:20:06.258123	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 05:20:06.480988	\N
10	activity_6810331325_1760764807_email	6810331325	payments	email	cameronwilson89@protonmail.com	2025-10-18 05:20:07.885835	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 05:20:08.105885	\N
11	activity_5590563715_1760764809_telegram	5590563715	payments	telegram	5590563715	2025-10-18 05:20:09.493444	2025-10-18 05:20:09.49082	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 05:20:09.712631	\N
12	activity_5590563715_1760764810_email	5590563715	payments	email	onarrival21@gmail.com	2025-10-18 05:20:10.731428	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 05:20:10.950313	\N
13	activity_7289467354_1760771666_telegram	7289467354	payments	telegram	7289467354	2025-10-18 07:14:26.334439	2025-10-18 07:14:25.900406	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 07:14:26.836014	\N
14	activity_7289467354_1760771666_email	7289467354	payments	email	Meganbaxter696@gmail.com	2025-10-18 07:14:26.334629	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 07:14:26.836014	\N
15	activity_7289467354_1760771676_telegram	7289467354	payments	telegram	7289467354	2025-10-18 07:14:36.328988	2025-10-18 07:14:36.325907	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 07:14:36.552817	\N
16	activity_7289467354_1760771677_email	7289467354	payments	email	Meganbaxter696@gmail.com	2025-10-18 07:14:37.965507	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 07:14:38.184648	\N
17	activity_5590563715_1760771679_telegram	5590563715	payments	telegram	5590563715	2025-10-18 07:14:39.466934	2025-10-18 07:14:39.463358	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 07:14:39.685673	\N
18	activity_5590563715_1760771680_email	5590563715	payments	email	onarrival21@gmail.com	2025-10-18 07:14:40.732687	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 07:14:40.951597	\N
19	activity_5590563715_1760779968_telegram	5590563715	payments	telegram	5590563715	2025-10-18 09:32:48.457469	2025-10-18 09:32:48.029438	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 09:32:48.675526	wallet_crypto_deposit_5590563715_ffdb60e9-150e-40a2-9c6c-3d21bcb97faf_confirmed
20	activity_5590563715_1760779968_email	5590563715	payments	email	onarrival21@gmail.com	2025-10-18 09:32:48.457661	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 09:32:48.675526	wallet_crypto_deposit_5590563715_ffdb60e9-150e-40a2-9c6c-3d21bcb97faf_confirmed
21	activity_5590563715_1760780483_telegram	5590563715	payments	telegram	5590563715	2025-10-18 09:41:23.725879	2025-10-18 09:41:23.225537	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 09:41:23.948513	wallet_crypto_deposit_5590563715_a6a507b6-a533-4807-b042-d770f5f6ca91_confirmed
22	activity_5590563715_1760780483_email	5590563715	payments	email	onarrival21@gmail.com	2025-10-18 09:41:23.726046	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 09:41:23.948513	wallet_crypto_deposit_5590563715_a6a507b6-a533-4807-b042-d770f5f6ca91_confirmed
23	activity_5168006768_1760780666_telegram	5168006768	escrow_updates	telegram	5168006768	2025-10-18 09:44:26.765731	2025-10-18 09:44:26.325747	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 09:44:26.985611	\N
24	activity_5168006768_1760780666_email	5168006768	escrow_updates	email	cloakhost@tutamail.com	2025-10-18 09:44:26.765901	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 09:44:26.985611	\N
25	activity_5590563715_1760780668_telegram	5590563715	escrow_updates	telegram	5590563715	2025-10-18 09:44:28.34724	2025-10-18 09:44:27.935069	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 09:44:28.563023	\N
26	activity_5590563715_1760780668_email	5590563715	escrow_updates	email	onarrival21@gmail.com	2025-10-18 09:44:28.347376	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 09:44:28.563023	\N
27	activity_5590563715_1760780683_telegram	5590563715	escrow_updates	telegram	5590563715	2025-10-18 09:44:43.929347	2025-10-18 09:44:43.530094	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 09:44:44.154329	\N
28	activity_5590563715_1760780683_email	5590563715	escrow_updates	email	onarrival21@gmail.com	2025-10-18 09:44:43.929528	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 09:44:44.154329	\N
29	activity_5168006768_1760780685_email	5168006768	escrow_updates	email	cloakhost@tutamail.com	2025-10-18 09:44:45.218191	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 09:44:45.44373	escrow_ES101825T98K_seller_accept_email
30	activity_5590563715_1760782132_telegram	5590563715	escrow_updates	telegram	5590563715	2025-10-18 10:08:52.948541	2025-10-18 10:08:52.543258	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 10:08:53.194776	\N
31	activity_5590563715_1760782132_email	5590563715	escrow_updates	email	onarrival21@gmail.com	2025-10-18 10:08:52.948726	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 10:08:53.194776	\N
32	activity_5168006768_1760782134_telegram	5168006768	escrow_updates	telegram	5168006768	2025-10-18 10:08:54.289384	2025-10-18 10:08:54.120305	\N	\N	\N	delivered	opened	1	\N	\N	2025-10-18 10:08:54.523223	\N
33	activity_5168006768_1760782134_email	5168006768	escrow_updates	email	cloakhost@tutamail.com	2025-10-18 10:08:54.289541	\N	\N	\N	\N	sent	opened	1	\N	\N	2025-10-18 10:08:54.523223	\N
\.


--
-- Data for Name: notification_preferences; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.notification_preferences (id, user_id, telegram_enabled, email_enabled, escrow_updates, payment_notifications, dispute_notifications, marketing_emails, security_alerts, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: notification_queue; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.notification_queue (id, user_id, channel, recipient, subject, content, template_name, template_data, status, priority, scheduled_at, sent_at, retry_count, error_message, idempotency_key) FROM stdin;
1	5168006768	telegram	5168006768	🎁 Welcome Bonus Received!	🎁 Welcome Bonus: $5.00 Trading Credit!\n\n✅ Use for: Escrow • Exchange • Fees\n⚠️ Not withdrawable (trading only)\n\nReady to trade? /menu	\N	{"broadcast_mode": true}	sent	2	2025-10-18 03:43:03.184209+00	2025-10-18 03:43:06.802686+00	0	\N	\N
2	5168006768	email	cloakhost@tutamail.com	🎁 Welcome Bonus Received!	🎁 Welcome Bonus: $5.00 Trading Credit!\n\n✅ Use for: Escrow • Exchange • Fees\n⚠️ Not withdrawable (trading only)\n\nReady to trade? /menu	\N	{"broadcast_mode": true}	sent	2	2025-10-18 03:43:03.184354+00	2025-10-18 03:43:08.436227+00	0	\N	\N
3	5590563715	telegram	5590563715	🎁 New Referral!	Hostbay Support joined via your link!\n\n💰 Earn $5.00 when they trade $100+\n📊 /menu → Invite Friends	\N	{"broadcast_mode": true}	sent	2	2025-10-18 03:43:03.613777+00	2025-10-18 03:43:09.979643+00	0	\N	\N
4	5590563715	email	onarrival21@gmail.com	🎁 New Referral!	Hostbay Support joined via your link!\n\n💰 Earn $5.00 when they trade $100+\n📊 /menu → Invite Friends	\N	{"broadcast_mode": true}	sent	2	2025-10-18 03:43:03.613895+00	2025-10-18 03:43:11.267881+00	0	\N	\N
5	6810331325	telegram	6810331325	🎁 Welcome Bonus Received!	🎁 Welcome Bonus: $5.00 Trading Credit!\n\n✅ Use for: Escrow • Exchange • Fees\n⚠️ Not withdrawable (trading only)\n\nReady to trade? /menu	\N	{"broadcast_mode": true}	sent	2	2025-10-18 05:19:47.790577+00	2025-10-18 05:20:06.683183+00	0	\N	\N
6	6810331325	email	cameronwilson89@protonmail.com	🎁 Welcome Bonus Received!	🎁 Welcome Bonus: $5.00 Trading Credit!\n\n✅ Use for: Escrow • Exchange • Fees\n⚠️ Not withdrawable (trading only)\n\nReady to trade? /menu	\N	{"broadcast_mode": true}	sent	2	2025-10-18 05:19:47.790716+00	2025-10-18 05:20:08.301094+00	0	\N	\N
7	5590563715	telegram	5590563715	🎁 New Referral!	Sal joined via your link!\n\n💰 Earn $5.00 when they trade $100+\n📊 /menu → Invite Friends	\N	{"broadcast_mode": true}	sent	2	2025-10-18 05:19:48.156601+00	2025-10-18 05:20:09.848287+00	0	\N	\N
8	5590563715	email	onarrival21@gmail.com	🎁 New Referral!	Sal joined via your link!\n\n💰 Earn $5.00 when they trade $100+\n📊 /menu → Invite Friends	\N	{"broadcast_mode": true}	sent	2	2025-10-18 05:19:48.156772+00	2025-10-18 05:20:11.08691+00	0	\N	\N
9	7289467354	telegram	7289467354	🎁 Welcome Bonus Received!	🎁 Welcome Bonus: $5.00 Trading Credit!\n\n✅ Use for: Escrow • Exchange • Fees\n⚠️ Not withdrawable (trading only)\n\nReady to trade? /menu	\N	{"broadcast_mode": true}	sent	2	2025-10-18 07:14:24.58254+00	2025-10-18 07:14:36.77261+00	0	\N	\N
10	7289467354	email	Meganbaxter696@gmail.com	🎁 Welcome Bonus Received!	🎁 Welcome Bonus: $5.00 Trading Credit!\n\n✅ Use for: Escrow • Exchange • Fees\n⚠️ Not withdrawable (trading only)\n\nReady to trade? /menu	\N	{"broadcast_mode": true}	sent	2	2025-10-18 07:14:24.582734+00	2025-10-18 07:14:38.341334+00	0	\N	\N
11	5590563715	telegram	5590563715	🎁 New Referral!	FREDDY joined via your link!\n\n💰 Earn $5.00 when they trade $100+\n📊 /menu → Invite Friends	\N	{"broadcast_mode": true}	sent	2	2025-10-18 07:14:24.986704+00	2025-10-18 07:14:39.843041+00	0	\N	\N
12	5590563715	email	onarrival21@gmail.com	🎁 New Referral!	FREDDY joined via your link!\n\n💰 Earn $5.00 when they trade $100+\n📊 /menu → Invite Friends	\N	{"broadcast_mode": true}	sent	2	2025-10-18 07:14:24.986843+00	2025-10-18 07:14:41.109074+00	0	\N	\N
\.


--
-- Data for Name: onboarding_sessions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.onboarding_sessions (id, user_id, current_step, email, invite_token, context_data, ip_address, user_agent, referral_source, email_captured_at, otp_verified_at, terms_accepted_at, completed_at, created_at, updated_at, expires_at) FROM stdin;
1	5590563715	done	onarrival21@gmail.com	\N	{"otp_verified_at": "2025-10-18T03:41:18.280631", "email_captured_at": "2025-10-18T03:40:22.910867"}	\N	\N	\N	2025-10-18 03:40:22.910867+00	2025-10-18 03:41:18.280631+00	\N	2025-10-18 03:41:23.023824+00	2025-10-18 03:35:20.425014+00	2025-10-18 03:41:22.934157+00	2025-10-19 03:35:20.503967+00
2	5168006768	done	cloakhost@tutamail.com	\N	{"otp_verified_at": "2025-10-18T03:42:57.950432", "email_captured_at": "2025-10-18T03:42:37.564033", "pending_referral_code": "FE22A9"}	\N	\N	\N	2025-10-18 03:42:37.564033+00	2025-10-18 03:42:57.950432+00	\N	2025-10-18 03:43:01.966225+00	2025-10-18 03:42:07.936471+00	2025-10-18 03:43:01.877699+00	2025-10-19 03:42:08.019196+00
4	5427296864	capture_email	\N	\N	{"pending_referral_code": "FE22A9"}	\N	\N	\N	\N	\N	\N	\N	2025-10-18 04:18:30.231511+00	2025-10-18 04:18:30.716518+00	2025-10-19 04:18:30.292216+00
5	6810331325	done	cameronwilson89@protonmail.com	\N	{"otp_verified_at": "2025-10-18T05:19:31.195072", "email_captured_at": "2025-10-18T05:18:59.826709", "pending_referral_code": "FE22A9"}	\N	\N	\N	2025-10-18 05:18:59.826709+00	2025-10-18 05:19:31.195072+00	\N	2025-10-18 05:19:46.456878+00	2025-10-18 05:18:25.864385+00	2025-10-18 05:19:46.379946+00	2025-10-19 05:18:25.94059+00
6	1789955723	capture_email	\N	\N	{"pending_referral_code": "FE22A9"}	\N	\N	\N	\N	\N	\N	\N	2025-10-18 05:23:23.569341+00	2025-10-18 05:23:24.105427+00	2025-10-19 05:23:23.644773+00
7	806528697	capture_email	\N	\N	{"pending_referral_code": "FE22A9"}	\N	\N	\N	\N	\N	\N	\N	2025-10-18 05:30:04.070807+00	2025-10-18 05:30:04.553113+00	2025-10-19 05:30:04.152401+00
9	7289467354	done	Meganbaxter696@gmail.com	\N	{"otp_verified_at": "2025-10-18T07:14:01.082009", "email_captured_at": "2025-10-18T07:13:16.047773", "pending_referral_code": "FE22A9"}	\N	\N	\N	2025-10-18 07:13:16.047773+00	2025-10-18 07:14:01.082009+00	\N	2025-10-18 07:14:23.13965+00	2025-10-18 07:12:26.376409+00	2025-10-18 07:14:23.047416+00	2025-10-19 07:12:26.46903+00
10	2097425528	capture_email	\N	\N	{}	\N	\N	\N	\N	\N	\N	\N	2025-10-18 07:44:22.519233+00	2025-10-18 07:44:22.519233+00	2025-10-19 07:44:22.609614+00
11	6903317845	capture_email	\N	\N	{"pending_referral_code": "FE22A9"}	\N	\N	\N	\N	\N	\N	\N	2025-10-18 08:00:39.003132+00	2025-10-18 08:00:39.664867+00	2025-10-19 08:00:38.592491+00
12	1531772316	capture_email	\N	\N	{}	\N	\N	\N	\N	\N	\N	\N	2025-10-18 08:02:49.137548+00	2025-10-18 08:02:49.137548+00	2025-10-19 08:02:49.222066+00
13	369576289	capture_email	\N	\N	{"pending_referral_code": "FE22A9"}	\N	\N	\N	\N	\N	\N	\N	2025-10-18 09:52:53.732506+00	2025-10-18 09:52:54.333144+00	2025-10-19 09:52:53.800358+00
\.


--
-- Data for Name: otp_verifications; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.otp_verifications (id, user_id, email, otp_code, verification_type, context_data, is_verified, created_at, expires_at) FROM stdin;
\.


--
-- Data for Name: outbox_events; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.outbox_events (id, event_type, aggregate_id, event_data, processed, created_at, processed_at, retry_count, last_error) FROM stdin;
\.


--
-- Data for Name: payment_addresses; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.payment_addresses (id, address, currency, provider, user_id, escrow_id, is_used, provider_data, created_at, used_at, utid) FROM stdin;
1	0x817ab4dde766a4bd85f425e577ec07066966ea22	ETH	dynopay	5590563715	1	f	{"address": "0x817ab4dde766a4bd85f425e577ec07066966ea22", "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAASwAAAEsCAYAAAB5fY51AAAAAklEQVR4AewaftIAAAe5SURBVO3BwW0kSRAEQY/E6K9yHBW44qPQmE6um6U/kKQFBklaYpCkJQZJWmKQpCUGSVpikKQlBklaYpCkJQZJWmKQpCUGSVpikKQlBklaYpCkJQZJWmKQpCUGSVpikKQlBklaYpCkJQZJWmKQpCUGSVpikKQlBklaYpCkJQZJWmKQpCUGSVpikKQlBklaYpCkJT68QBL+urbcSMI3tWW7JJy05UYS/rq2fNMgSUsMkrTEIElLDJK0xCBJSwyStMQgSUt8WKAtb5eEb2rLSRJuJOGkLb9JwklbTpJwoy3f1Ja3S8KbDZK0xCBJSwyStMQgSUsMkrTEIElLDJK0xIc/IAlPasvTknDSlhttOUnCSVtOkvC0tpwk4UYSTtrytCQ8qS2bDZK0xCBJSwyStMQgSUsMkrTEIElLDJK0xAf9CUk4acuNJJy05TdJuJEE/dsGSVpikKQlBklaYpCkJQZJWmKQpCUGSVrig1ZIwklbTpJw0paTJNxqy4223EjCSVv0boMkLTFI0hKDJC0xSNISgyQtMUjSEoMkLfHhD2iLztpykoSnJeFGW2605e3aov83SNISgyQtMUjSEoMkLTFI0hKDJC0xSNISgyQt8WGBJPzr2nKShJO23GjLSRJ+05aTJNxIwklbTpJw0pYbSdCdQZKWGCRpiUGSlhgkaYlBkpYYJGmJQZKWSH+gr0vCN7XlRhJuteVJSbjRFn3XIElLDJK0xCBJSwyStMQgSUsMkrTEIElLpD/4siSctOUkCW/XlhtJOGnLjSSctOVWEk7acpKEk7Z8UxLeri2bDZK0xCBJSwyStMQgSUsMkrTEIElLDJK0RPqDl0vCSVtOknDSlqcl4aQt35SEG225lYSTtpwk4UltOUnCSVt+k4STtjwpCSdt+aZBkpYYJGmJQZKWGCRpiUGSlhgkaYlBkpZIf6BrSThpy0kS3qwtt5Jwoy1PSsJJW24k4TdtOUnCSVtOknDSljcbJGmJQZKWGCRpiUGSlhgkaYlBkpYYJGmJD39AEr6tLSdJOGnLjSSctOUkCSdJuNWWkyS8WRKeloSTtvzLBklaYpCkJQZJWmKQpCUGSVpikKQlBkla4sMLJOGb2nIrCSdtuZGEk7acJOGkLU9LwklbTpJwoy1PastJEn7TlpMkPCkJJ235pkGSlhgkaYlBkpYYJGmJQZKWGCRpiUGSlvjwD2jLSRJuteVGEr4pCSdtOUnCb9pyoy03knDSlhtJOGnLb5Jwoy03kvBmgyQtMUjSEoMkLTFI0hKDJC0xSNISgyQtkf7gy5Jw0pYbSbjRlt8k4UZbbiThRlv0rCS8XVvebJCkJQZJWmKQpCUGSVpikKQlBklaYpCkJQZJWiL9wcsl4UZbTpJwqy03kvDXteUkCSdt+aYkvF1bTpJw0pY3GyRpiUGSlhgkaYlBkpYYJGmJQZKWGCRpiQ8vkIQbbXlSW36ThDdry0kSTtpyKwknbTlJwje15e2ScCMJJ235pkGSlhgkaYlBkpYYJGmJQZKWGCRpiUGSlvjwD0jC09pykoQbbXmzJNxKwklbbiThpC0nSfi2tpy05UYS3myQpCUGSVpikKQlBklaYpCkJQZJWmKQpCU+LNCWG205ScKtJJy05UYS3qwtv0nCSVtOknDSlpO2PKktt5JwkoSTttxoy5sNkrTEIElLDJK0xCBJSwyStMQgSUsMkrTEB9GWkyT8pi3f1Ja/ri1PSsJJW24k4duScNKWNxskaYlBkpYYJGmJQZKWGCRpiUGSlhgkaYkPf0ASTtrytCR8UxKe1JZvS8KNttxIwre15SQJf9kgSUsMkrTEIElLDJK0xCBJSwyStMQgSUukP9DXJWGztmyXhJO2PC0JJ215UhJO2vJNgyQtMUjSEoMkLTFI0hKDJC0xSNISgyQt8eEFkvDXteWkLSdJuNGWkyTcSMKttpwk4aQtJ0l4UhJO2vK0JNxoy5sNkrTEIElLDJK0xCBJSwyStMQgSUsMkrTEhwXa8nZJuJGEG205ScJJW06ScNKW3yThRlverC3f1paTJJwk4aQt3zRI0hKDJC0xSNISgyQtMUjSEoMkLTFI0hKDJC3x4Q9IwpPa8q9ry0kSbiXhRltO2nKShJMkfFsSbrTlJAlvNkjSEoMkLTFI0hKDJC0xSNISgyQtMUjSEh+0QltOknAjCSdtOWnLb5Jw0pYbSThpy5Pa8rQknLTlRlvebJCkJQZJWmKQpCUGSVpikKQlBklaYpCkJT7on9CWkyScJOFpSThpy0lbbrTlRhKe1pYbSThpy5sNkrTEIElLDJK0xCBJSwyStMQgSUsMkrTEhz+gLdu15SQJN5LwpLZsl4STtpy05VYSTpJw0pa/bJCkJQZJWmKQpCUGSVpikKQlBklaYpCkJT4skIS/Lgk32vJ2SThpy0kSTtpykoSTtpwk4aQtJ0m41ZaTJJy0ZbNBkpYYJGmJQZKWGCRpiUGSlhgkaYlBkpZIfyBJCwyStMQgSUsMkrTEIElLDJK0xCBJSwyStMQgSUsMkrTEIElLDJK0xCBJSwyStMQgSUsMkrTEIElLDJK0xCBJSwyStMQgSUsMkrTEIElLDJK0xCBJSwyStMQgSUsMkrTEIElLDJK0xCBJSwyStMR/ju08cMAz6xUAAAAASUVORK5CYII=", "address_in": "0x817ab4dde766a4bd85f425e577ec07066966ea22", "address_out": null, "fee_percent": 1.0, "qr_code_svg": null, "callback_url": "https://lockbay.replit.app/webhook/dynopay/escrow", "reference_id": "ES101825T98K", "minimum_transaction": 0.00001}	2025-10-18 09:42:16.293828+00	\N	ES101825T98K
\.


--
-- Data for Name: pending_cashouts; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.pending_cashouts (id, token, signature, user_id, amount, currency, withdrawal_address, network, fee_amount, net_amount, fee_breakdown, metadata, created_at, expires_at, updated_at) FROM stdin;
\.


--
-- Data for Name: platform_revenue; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.platform_revenue (id, escrow_id, fee_amount, fee_currency, fee_type, source_transaction_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: ratings; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.ratings (id, escrow_id, rater_id, rated_id, rating, comment, category, created_at, updated_at, is_dispute_rating, dispute_outcome, dispute_resolution_type) FROM stdin;
\.


--
-- Data for Name: refunds; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.refunds (id, refund_id, user_id, refund_type, amount, currency, reason, cashout_id, escrow_id, transaction_id, status, idempotency_key, processed_by, balance_before, balance_after, admin_approved, admin_approved_by, admin_approved_at, error_message, retry_count, archived_at, archive_reason, created_at, completed_at, failed_at) FROM stdin;
\.


--
-- Data for Name: saga_steps; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.saga_steps (id, saga_id, step_name, status, step_data, error_message, created_at, completed_at) FROM stdin;
\.


--
-- Data for Name: saved_addresses; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.saved_addresses (id, user_id, currency, network, address, label, is_verified, verification_sent, created_at, last_used, is_active) FROM stdin;
\.


--
-- Data for Name: saved_bank_accounts; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.saved_bank_accounts (id, user_id, account_number, bank_code, bank_name, account_name, label, is_default, is_active, is_verified, verification_sent, created_at, last_used) FROM stdin;
\.


--
-- Data for Name: security_audits; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.security_audits (id, user_id, action_type, resource_type, resource_id, ip_address, user_agent, success, risk_level, description, context_data, created_at) FROM stdin;
\.


--
-- Data for Name: support_messages; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.support_messages (id, ticket_id, sender_id, message, is_admin_reply, created_at) FROM stdin;
\.


--
-- Data for Name: support_tickets; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.support_tickets (id, user_id, subject, description, status, priority, category, assigned_to, admin_notes, created_at, updated_at, resolved_at, ticket_id) FROM stdin;
\.


--
-- Data for Name: system_config; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.system_config (key, value, value_type, description, is_public, is_encrypted, created_at, updated_at, updated_by) FROM stdin;
maintenance_duration	60	integer	Estimated maintenance duration in minutes (NULL for unspecified)	f	f	2025-10-18 09:22:10.825649+00	2025-10-18 11:48:59.556377+00	1531772316
maintenance_start_time	2025-10-18T11:48:59.429794+00:00	timestamp	Timestamp when maintenance mode was enabled	f	f	2025-10-18 09:22:10.825649+00	2025-10-18 11:48:59.556377+00	1531772316
maintenance_end_time	2025-10-18T12:48:59.429794+00:00	timestamp	Calculated end time for maintenance (start + duration)	f	f	2025-10-18 09:22:10.825649+00	2025-10-18 11:48:59.556377+00	1531772316
maintenance_mode	true	boolean	Global maintenance mode - when true, only admins can access the bot	f	f	2025-10-18 09:22:11.191325+00	2025-10-18 11:49:00.025915+00	1531772316
\.


--
-- Data for Name: transaction_engine_events; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.transaction_engine_events (id, event_id, transaction_id, saga_id, event_type, event_category, event_data, previous_state, new_state, triggered_by, user_id, created_at) FROM stdin;
\.


--
-- Data for Name: transactions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.transactions (id, transaction_id, user_id, transaction_type, amount, currency, fee, status, provider, external_id, external_tx_id, blockchain_tx_hash, escrow_id, cashout_id, description, extra_data, created_at, updated_at, confirmed_at, utid) FROM stdin;
1	12511536-a0b9-4bf3-a9c7-20d7c8074d16	5168006768	referral_welcome_bonus	5.000000000000000000	USD	\N	completed	\N	\N	\N	\N	\N	\N	🎁 Welcome Bonus: $5 Trading Credit (use for escrow/exchange, not withdrawable) - Ref: REF_WELCOME_5168006768_1760758982	\N	2025-10-18 03:43:01.877699+00	\N	2025-10-18 03:43:02.868403+00	\N
2	e6d1da8d-a4dc-4b28-910d-8efbe9cf9b3c	6810331325	referral_welcome_bonus	5.000000000000000000	USD	\N	completed	\N	\N	\N	\N	\N	\N	🎁 Welcome Bonus: $5 Trading Credit (use for escrow/exchange, not withdrawable) - Ref: REF_WELCOME_6810331325_1760764786	\N	2025-10-18 05:19:46.379946+00	\N	2025-10-18 05:19:47.486368+00	\N
3	baad871d-11e3-4f32-9d4a-b723da808b84	7289467354	referral_welcome_bonus	5.000000000000000000	USD	\N	completed	\N	\N	\N	\N	\N	\N	🎁 Welcome Bonus: $5 Trading Credit (use for escrow/exchange, not withdrawable) - Ref: REF_WELCOME_7289467354_1760771663	\N	2025-10-18 07:14:23.047416+00	\N	2025-10-18 07:14:24.221273+00	\N
4	TX101825T3KN	5590563715	deposit	22.514962000000000000	USD	\N	confirmed	\N	\N	\N	ffdb60e9-150e-40a2-9c6c-3d21bcb97faf	\N	\N	DynoPay wallet deposit - 0.005800 ETH → $22.51 USD	\N	2025-10-18 09:32:45.530836+00	\N	2025-10-18 09:32:45.530836+00	\N
5	TX101825ZMKW	5590563715	deposit	14.739288000000000000	USD	\N	confirmed	\N	\N	\N	a6a507b6-a533-4807-b042-d770f5f6ca91	\N	\N	DynoPay wallet deposit - 0.003800 ETH → $14.74 USD	\N	2025-10-18 09:41:20.91415+00	\N	2025-10-18 09:41:20.91415+00	\N
6	286dbc3e-e963-4a94-8b01-7a59e341a26b	5590563715	escrow_overpayment	4.140000000000000000	USD	\N	completed	\N	\N	\N	\N	1	\N	Overpayment credit from escrow ES101825T98K: +$4.14	\N	2025-10-18 09:44:20.921009+00	\N	2025-10-18 09:44:22.975904+00	\N
7	ESC_ES101825T98K_de7ba9b8	5590563715	escrow_payment	30.000000000000000000	USD	\N	confirmed	\N	\N	\N	de7ba9b8-8fcf-4e67-8aaf-24c0ebc0617b	1	\N	Escrow deposit for ES101825T98K	\N	2025-10-18 09:44:20.921009+00	\N	2025-10-18 09:44:23.395734+00	\N
\.


--
-- Data for Name: unified_transaction_retry_logs; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.unified_transaction_retry_logs (id, transaction_id, retry_attempt, retry_reason, error_code, error_message, error_details, retry_strategy, delay_seconds, next_retry_at, external_provider, external_response_code, external_response_body, retry_successful, final_retry, attempted_at, completed_at, duration_ms) FROM stdin;
\.


--
-- Data for Name: unified_transaction_status_history; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.unified_transaction_status_history (id, transaction_id, from_status, to_status, change_reason, changed_by, system_action, changed_at) FROM stdin;
\.


--
-- Data for Name: unified_transactions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.unified_transactions (id, user_id, transaction_type, status, amount, currency, fee, phase, external_id, reference_id, metadata, created_at, updated_at, description) FROM stdin;
\.


--
-- Data for Name: user_achievements; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.user_achievements (id, user_id, achievement_type, achievement_name, achievement_description, achievement_tier, target_value, current_value, achieved, reward_message, badge_emoji, points_awarded, first_eligible_at, achieved_at, created_at, trigger_transaction_id, trigger_escrow_id, additional_context) FROM stdin;
\.


--
-- Data for Name: user_contacts; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.user_contacts (id, contact_id, user_id, contact_type, contact_value, is_verified, verified_at, verification_code, verification_expires, verification_attempts, is_primary, last_used, is_active, notifications_enabled, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: user_sessions; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.user_sessions (session_id, user_id, session_type, status, data, created_at, expires_at, last_accessed) FROM stdin;
\.


--
-- Data for Name: user_sms_usage; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.user_sms_usage (id, user_id, date, sms_count, last_sms_sent_at, phone_numbers_contacted, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: user_streak_tracking; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.user_streak_tracking (id, user_id, daily_activity_streak, best_daily_activity_streak, activity_reset_count, last_activity_date, successful_trades_streak, best_successful_trades_streak, successful_trades_reset_count, last_successful_trade_date, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.users (id, telegram_id, username, first_name, last_name, phone_number, email, email_verified, language_code, timezone, created_at, updated_at, last_activity, is_active, is_verified, is_blocked, is_admin, is_seller, auto_cashout_enabled, auto_cashout_crypto_address_id, auto_cashout_bank_account_id, status, conversation_state, terms_accepted_at, onboarded_at, onboarding_completed, referral_code, referred_by_id, total_referrals, referral_earnings, reputation_score, completed_trades, successful_trades, failed_trades, avg_rating, total_ratings, profile_image_url, bio, cashout_preference, universal_welcome_bonus_given, universal_welcome_bonus_given_at, profile_slug) FROM stdin;
6810331325	6810331325	Xlookups	Sal	\N	\N	cameronwilson89@protonmail.com	t	\N	\N	2025-10-18 05:18:24.444852	2025-10-18 05:18:59.826709	2025-10-18 05:20:38.67309	t	t	f	f	f	f	\N	\N	active	description_input	2025-10-18 05:19:46.456878+00	2025-10-18 05:19:46.456878+00	t	BD852E	5590563715	0	0.00000000	0	0	0	0	0.00	0	\N	\N	\N	f	\N	xlookups
1789955723	1789955723	Gentleman8643	GENTLEMAN	\N	\N	temp_1789955723@onboarding.temp	f	\N	\N	2025-10-18 05:23:22.443054	2025-10-18 05:23:22.443054	\N	t	f	f	f	f	f	\N	\N	\N	\N	\N	\N	f	E728A2	\N	0	0.00000000	0	0	0	0	0.00	0	\N	\N	\N	f	\N	gentleman8643
6836641696	6836641696	BitcoinBlackOG	BitcoinBlack	\N	\N	temp_6836641696@onboarding.temp	f	\N	\N	2025-10-18 04:15:25.138488	2025-10-18 04:15:25.138488	\N	t	f	f	f	f	f	\N	\N	\N	\N	\N	\N	f	766479	\N	0	0.00000000	0	0	0	0	0.00	0	\N	\N	\N	f	\N	bitcoinblackog
5427296864	5427296864	m_maker2	M-maker	\N	\N	temp_5427296864@onboarding.temp	f	\N	\N	2025-10-18 04:18:29.015518	2025-10-18 04:18:29.015518	\N	t	f	f	f	f	f	\N	\N	\N	\N	\N	\N	f	29B072	\N	0	0.00000000	0	0	0	0	0.00	0	\N	\N	\N	f	\N	m_maker2
806528697	806528697	aryormhidey	You	\N	\N	temp_806528697@onboarding.temp	f	\N	\N	2025-10-18 05:30:02.717434	2025-10-18 05:30:02.717434	\N	t	f	f	f	f	f	\N	\N	\N	\N	\N	\N	f	2D1D12	\N	0	0.00000000	0	0	0	0	0.00	0	\N	\N	\N	f	\N	aryormhidey
7448028858	7448028858	orbitallight	Orbital	Light	\N	qwfawfwafwq@redgre.com	f	\N	\N	2025-10-18 05:56:48.566728	2025-10-18 05:57:21.303306	\N	t	f	f	f	f	f	\N	\N	\N	\N	\N	\N	f	A8E580	\N	0	0.00000000	0	0	0	0	0.00	0	\N	\N	\N	f	\N	orbitallight
1531772316	1531772316	globalservicehelp	Onboard Admin	\N	\N	temp_1531772316@onboarding.temp	f	\N	\N	2025-10-18 08:02:48.128872	2025-10-18 08:02:48.128872	\N	t	f	f	f	f	f	\N	\N	\N	admin_broadcast_	\N	\N	f	4A9461	\N	0	0.00000000	0	0	0	0	0.00	0	\N	\N	\N	f	\N	globalservicehelp
369576289	369576289	Sha_gy	Shagy	\N	\N	temp_369576289@onboarding.temp	f	\N	\N	2025-10-18 09:52:52.181365	2025-10-18 09:52:52.181365	\N	t	f	f	f	f	f	\N	\N	\N	\N	\N	\N	f	C1633C	\N	0	0.00000000	0	0	0	0	0.00	0	\N	\N	\N	f	\N	sha_gy
7289467354	7289467354	Omnicare01	FREDDY	WINNIE	\N	Meganbaxter696@gmail.com	t	\N	\N	2025-10-18 07:12:24.570839	2025-10-18 07:13:16.047773	2025-10-18 07:16:09.617987	t	t	f	f	f	f	\N	\N	active	\N	2025-10-18 07:14:23.13965+00	2025-10-18 07:14:23.13965+00	t	DD47C5	5590563715	0	0.00000000	0	0	0	0	0.00	0	\N	\N	\N	f	\N	omnicare01
2097425528	2097425528	RonnieNico	RONNIE	NiCOLAS	\N	temp_2097425528@onboarding.temp	f	\N	\N	2025-10-18 07:44:21.427068	2025-10-18 07:44:21.427068	\N	t	f	f	f	f	f	\N	\N	\N	\N	\N	\N	f	3BEC99	\N	0	0.00000000	0	0	0	0	0.00	0	\N	\N	\N	f	\N	ronnienico
6903317845	6903317845	hradminkelvin	Kelvin	Whitemore	\N	temp_6903317845@onboarding.temp	f	\N	\N	2025-10-18 08:00:37.004551	2025-10-18 08:00:37.004551	\N	t	f	f	f	f	f	\N	\N	\N	\N	\N	\N	f	C043B4	\N	0	0.00000000	0	0	0	0	0.00	0	\N	\N	\N	f	\N	hradminkelvin
5168006768	5168006768	Hostbay_support	Hostbay Support	\N	\N	cloakhost@tutamail.com	t	\N	\N	2025-10-18 03:42:06.426967	2025-10-18 03:42:37.564033	2025-10-18 08:11:52.478683	t	t	f	f	f	f	\N	\N	active	\N	2025-10-18 03:43:01.966225+00	2025-10-18 03:43:01.966225+00	t	1AEB9D	5590563715	0	0.00000000	0	0	0	0	0.00	0	\N	\N	\N	f	\N	hostbay_support
5590563715	5590563715	onarrival1	Gold	\N	\N	onarrival21@gmail.com	t	\N	\N	2025-10-18 03:35:19.319943	2025-10-18 03:40:22.910867	2025-10-18 11:46:02.308626	t	t	f	f	f	f	\N	\N	active	\N	2025-10-18 03:41:23.023824+00	2025-10-18 03:41:23.023824+00	t	FE22A9	\N	0	0.00000000	0	0	0	0	0.00	0	\N	\N	\N	f	\N	onarrival1
\.


--
-- Data for Name: wallet_balance_snapshots; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.wallet_balance_snapshots (id, snapshot_id, wallet_type, user_id, wallet_id, internal_wallet_id, currency, available_balance, frozen_balance, locked_balance, reserved_balance, total_balance, snapshot_type, trigger_event, previous_snapshot_id, balance_checksum, transaction_count, last_transaction_id, validation_passed, validation_errors, created_at, valid_from, valid_until, created_by, hostname, process_id, snapshot_metadata, notes) FROM stdin;
\.


--
-- Data for Name: wallet_holds; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.wallet_holds (id, user_id, currency, amount, hold_type, reference_id, status, created_at, expires_at, released_at) FROM stdin;
\.


--
-- Data for Name: wallets; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.wallets (id, user_id, currency, available_balance, frozen_balance, created_at, updated_at, utid, trading_credit) FROM stdin;
2	5168006768	USD	0.000000000000000000	0.000000000000000000	2025-10-18 03:42:06.344534+00	2025-10-18 03:43:01.877699+00	\N	5.000000000000000000
3	6836641696	USD	0.000000000000000000	0.000000000000000000	2025-10-18 04:15:25.037805+00	2025-10-18 04:15:25.037805+00	\N	0.000000000000000000
4	5427296864	USD	0.000000000000000000	0.000000000000000000	2025-10-18 04:18:28.955073+00	2025-10-18 04:18:28.955073+00	\N	0.000000000000000000
5	6810331325	USD	0.000000000000000000	0.000000000000000000	2025-10-18 05:18:24.308609+00	2025-10-18 05:19:46.379946+00	\N	5.000000000000000000
6	1789955723	USD	0.000000000000000000	0.000000000000000000	2025-10-18 05:23:22.366729+00	2025-10-18 05:23:22.366729+00	\N	0.000000000000000000
7	806528697	USD	0.000000000000000000	0.000000000000000000	2025-10-18 05:30:02.636323+00	2025-10-18 05:30:02.636323+00	\N	0.000000000000000000
8	7448028858	USD	0.000000000000000000	0.000000000000000000	2025-10-18 05:56:48.424484+00	2025-10-18 05:56:48.424484+00	\N	0.000000000000000000
9	7289467354	USD	0.000000000000000000	0.000000000000000000	2025-10-18 07:12:24.417111+00	2025-10-18 07:14:23.047416+00	\N	5.000000000000000000
10	2097425528	USD	0.000000000000000000	0.000000000000000000	2025-10-18 07:44:21.275292+00	2025-10-18 07:44:21.275292+00	\N	0.000000000000000000
11	6903317845	USD	0.000000000000000000	0.000000000000000000	2025-10-18 08:00:37.405105+00	2025-10-18 08:00:37.405105+00	\N	0.000000000000000000
12	1531772316	USD	0.000000000000000000	0.000000000000000000	2025-10-18 08:02:48.046553+00	2025-10-18 08:02:48.046553+00	\N	0.000000000000000000
1	5590563715	USD	41.390000000000000000	0.000000000000000000	2025-10-18 03:35:19.182716+00	2025-10-18 09:44:20.921009+00	\N	0.000000000000000000
13	369576289	USD	0.000000000000000000	0.000000000000000000	2025-10-18 09:52:52.113285+00	2025-10-18 09:52:52.113285+00	\N	0.000000000000000000
\.


--
-- Data for Name: webhook_event_ledger; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.webhook_event_ledger (id, event_provider, event_id, event_type, payload, txid, reference_id, status, amount, currency, processed_at, completed_at, webhook_payload, processing_result, error_message, retry_count, user_id, event_metadata, processing_duration_ms, created_at, updated_at) FROM stdin;
1	dynopay	de7ba9b8-8fcf-4e67-8aaf-24c0ebc0617b	escrow_deposit	"{\\"id\\": \\"de7ba9b8-8fcf-4e67-8aaf-24c0ebc0617b\\", \\"payment_mode\\": \\"CRYPTO\\", \\"base_amount\\": \\"34.15\\", \\"base_currency\\": \\"USD\\", \\"paid_amount\\": \\"0.008800\\", \\"paid_currency\\": \\"ETH\\", \\"transaction_reference\\": \\"0x86517abc2e7b1098dfcc89b9d6cd508ed9f84ca95a8d8789e5a59616f1da36ee\\", \\"transaction_type\\": \\"PAYMENT\\", \\"transaction_details\\": \\"Made payment for escrow_deposit on Nomadly1\\", \\"status\\": \\"successful\\", \\"meta_data\\": {\\"product_name\\": \\"escrow_deposit\\", \\"refId\\": \\"ES101825T98K\\", \\"user_id\\": null, \\"escrow_id\\": \\"ES101825T98K\\"}}"	de7ba9b8-8fcf-4e67-8aaf-24c0ebc0617b	ES101825T98K	completed	0.008800000000000000	ETH	2025-10-18 09:44:20.208778+00	2025-10-18 09:44:29.171899+00	"{\\"id\\": \\"de7ba9b8-8fcf-4e67-8aaf-24c0ebc0617b\\", \\"payment_mode\\": \\"CRYPTO\\", \\"base_amount\\": \\"34.15\\", \\"base_currency\\": \\"USD\\", \\"paid_amount\\": \\"0.008800\\", \\"paid_currency\\": \\"ETH\\", \\"transaction_reference\\": \\"0x86517abc2e7b1098dfcc89b9d6cd508ed9f84ca95a8d8789e5a59616f1da36ee\\", \\"transaction_type\\": \\"PAYMENT\\", \\"transaction_details\\": \\"Made payment for escrow_deposit on Nomadly1\\", \\"status\\": \\"successful\\", \\"meta_data\\": {\\"product_name\\": \\"escrow_deposit\\", \\"refId\\": \\"ES101825T98K\\", \\"user_id\\": null, \\"escrow_id\\": \\"ES101825T98K\\"}}"	{"status": "success", "escrow_id": "ES101825T98K", "transaction_id": "ESC_ES101825T98K_de7ba9b8", "amount_received": "0.008800", "currency": "ETH", "usd_value": "34.1422400"}	\N	0	\N	{"meta_data": {"product_name": "escrow_deposit", "refId": "ES101825T98K", "user_id": null, "escrow_id": "ES101825T98K"}, "webhook_source": "dynopay_escrow_deposit", "timestamp": "2025-10-18T09:44:19.845687+00:00"}	9222	2025-10-18 09:44:20.208778+00	2025-10-18 09:44:29.171899+00
\.


--
-- Name: replit_database_migrations_v1_id_seq; Type: SEQUENCE SET; Schema: _system; Owner: neondb_owner
--

SELECT pg_catalog.setval('_system.replit_database_migrations_v1_id_seq', 2, true);


--
-- Name: admin_action_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.admin_action_tokens_id_seq', 1, false);


--
-- Name: admin_operation_overrides_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.admin_operation_overrides_id_seq', 1, false);


--
-- Name: audit_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.audit_events_id_seq', 6, true);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 1, false);


--
-- Name: balance_alert_state_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.balance_alert_state_id_seq', 1, true);


--
-- Name: balance_audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.balance_audit_logs_id_seq', 1, false);


--
-- Name: balance_protection_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.balance_protection_logs_id_seq', 1, false);


--
-- Name: balance_reconciliation_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.balance_reconciliation_logs_id_seq', 1, false);


--
-- Name: cashouts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.cashouts_id_seq', 1, false);


--
-- Name: crypto_deposits_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.crypto_deposits_id_seq', 2, true);


--
-- Name: dispute_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.dispute_messages_id_seq', 1, false);


--
-- Name: disputes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.disputes_id_seq', 1, false);


--
-- Name: distributed_locks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.distributed_locks_id_seq', 1, true);


--
-- Name: email_verifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.email_verifications_id_seq', 6, true);


--
-- Name: escrow_holdings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.escrow_holdings_id_seq', 1, true);


--
-- Name: escrow_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.escrow_messages_id_seq', 1, true);


--
-- Name: escrow_refund_operations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.escrow_refund_operations_id_seq', 1, false);


--
-- Name: escrows_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.escrows_id_seq', 1, true);


--
-- Name: exchange_orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.exchange_orders_id_seq', 1, false);


--
-- Name: idempotency_keys_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.idempotency_keys_id_seq', 1, true);


--
-- Name: idempotency_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.idempotency_tokens_id_seq', 1, false);


--
-- Name: inbox_webhooks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.inbox_webhooks_id_seq', 1, false);


--
-- Name: internal_wallets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.internal_wallets_id_seq', 1, false);


--
-- Name: notification_activities_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.notification_activities_id_seq', 33, true);


--
-- Name: notification_preferences_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.notification_preferences_id_seq', 1, false);


--
-- Name: notification_queue_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.notification_queue_id_seq', 12, true);


--
-- Name: onboarding_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.onboarding_sessions_id_seq', 13, true);


--
-- Name: otp_verifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.otp_verifications_id_seq', 1, false);


--
-- Name: outbox_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.outbox_events_id_seq', 1, false);


--
-- Name: payment_addresses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.payment_addresses_id_seq', 1, true);


--
-- Name: pending_cashouts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.pending_cashouts_id_seq', 1, false);


--
-- Name: platform_revenue_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.platform_revenue_id_seq', 1, false);


--
-- Name: ratings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.ratings_id_seq', 1, false);


--
-- Name: refunds_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.refunds_id_seq', 1, false);


--
-- Name: saga_steps_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.saga_steps_id_seq', 1, false);


--
-- Name: saved_addresses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.saved_addresses_id_seq', 1, false);


--
-- Name: saved_bank_accounts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.saved_bank_accounts_id_seq', 1, false);


--
-- Name: security_audits_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.security_audits_id_seq', 1, false);


--
-- Name: support_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.support_messages_id_seq', 1, false);


--
-- Name: support_tickets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.support_tickets_id_seq', 1, false);


--
-- Name: transaction_engine_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.transaction_engine_events_id_seq', 1, false);


--
-- Name: transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.transactions_id_seq', 7, true);


--
-- Name: unified_transaction_retry_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.unified_transaction_retry_logs_id_seq', 1, false);


--
-- Name: unified_transaction_status_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.unified_transaction_status_history_id_seq', 1, false);


--
-- Name: unified_transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.unified_transactions_id_seq', 1, false);


--
-- Name: user_achievements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.user_achievements_id_seq', 1, false);


--
-- Name: user_contacts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.user_contacts_id_seq', 1, false);


--
-- Name: user_sms_usage_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.user_sms_usage_id_seq', 1, false);


--
-- Name: user_streak_tracking_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.user_streak_tracking_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.users_id_seq', 1, false);


--
-- Name: wallet_balance_snapshots_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.wallet_balance_snapshots_id_seq', 1, false);


--
-- Name: wallet_holds_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.wallet_holds_id_seq', 1, false);


--
-- Name: wallets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.wallets_id_seq', 13, true);


--
-- Name: webhook_event_ledger_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.webhook_event_ledger_id_seq', 1, true);


--
-- Name: replit_database_migrations_v1 replit_database_migrations_v1_pkey; Type: CONSTRAINT; Schema: _system; Owner: neondb_owner
--

ALTER TABLE ONLY _system.replit_database_migrations_v1
    ADD CONSTRAINT replit_database_migrations_v1_pkey PRIMARY KEY (id);


--
-- Name: admin_action_tokens admin_action_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.admin_action_tokens
    ADD CONSTRAINT admin_action_tokens_pkey PRIMARY KEY (id);


--
-- Name: admin_action_tokens admin_action_tokens_token_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.admin_action_tokens
    ADD CONSTRAINT admin_action_tokens_token_key UNIQUE (token);


--
-- Name: admin_operation_overrides admin_operation_overrides_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.admin_operation_overrides
    ADD CONSTRAINT admin_operation_overrides_pkey PRIMARY KEY (id);


--
-- Name: audit_events audit_events_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: balance_alert_state balance_alert_state_alert_key_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.balance_alert_state
    ADD CONSTRAINT balance_alert_state_alert_key_key UNIQUE (alert_key);


--
-- Name: balance_alert_state balance_alert_state_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.balance_alert_state
    ADD CONSTRAINT balance_alert_state_pkey PRIMARY KEY (id);


--
-- Name: balance_audit_logs balance_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.balance_audit_logs
    ADD CONSTRAINT balance_audit_logs_pkey PRIMARY KEY (id);


--
-- Name: balance_protection_logs balance_protection_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.balance_protection_logs
    ADD CONSTRAINT balance_protection_logs_pkey PRIMARY KEY (id);


--
-- Name: balance_reconciliation_logs balance_reconciliation_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.balance_reconciliation_logs
    ADD CONSTRAINT balance_reconciliation_logs_pkey PRIMARY KEY (id);


--
-- Name: cashouts cashouts_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.cashouts
    ADD CONSTRAINT cashouts_pkey PRIMARY KEY (id);


--
-- Name: cashouts cashouts_utid_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.cashouts
    ADD CONSTRAINT cashouts_utid_key UNIQUE (utid);


--
-- Name: crypto_deposits crypto_deposits_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.crypto_deposits
    ADD CONSTRAINT crypto_deposits_pkey PRIMARY KEY (id);


--
-- Name: dispute_messages dispute_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.dispute_messages
    ADD CONSTRAINT dispute_messages_pkey PRIMARY KEY (id);


--
-- Name: disputes disputes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.disputes
    ADD CONSTRAINT disputes_pkey PRIMARY KEY (id);


--
-- Name: distributed_locks distributed_locks_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.distributed_locks
    ADD CONSTRAINT distributed_locks_pkey PRIMARY KEY (id);


--
-- Name: email_verifications email_verifications_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.email_verifications
    ADD CONSTRAINT email_verifications_pkey PRIMARY KEY (id);


--
-- Name: escrow_holdings escrow_holdings_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrow_holdings
    ADD CONSTRAINT escrow_holdings_pkey PRIMARY KEY (id);


--
-- Name: escrow_messages escrow_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrow_messages
    ADD CONSTRAINT escrow_messages_pkey PRIMARY KEY (id);


--
-- Name: escrow_refund_operations escrow_refund_operations_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrow_refund_operations
    ADD CONSTRAINT escrow_refund_operations_pkey PRIMARY KEY (id);


--
-- Name: escrows escrows_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrows
    ADD CONSTRAINT escrows_pkey PRIMARY KEY (id);


--
-- Name: exchange_orders exchange_orders_exchange_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.exchange_orders
    ADD CONSTRAINT exchange_orders_exchange_id_key UNIQUE (exchange_id);


--
-- Name: exchange_orders exchange_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.exchange_orders
    ADD CONSTRAINT exchange_orders_pkey PRIMARY KEY (id);


--
-- Name: idempotency_keys idempotency_keys_operation_key_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.idempotency_keys
    ADD CONSTRAINT idempotency_keys_operation_key_key UNIQUE (operation_key);


--
-- Name: idempotency_keys idempotency_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.idempotency_keys
    ADD CONSTRAINT idempotency_keys_pkey PRIMARY KEY (id);


--
-- Name: idempotency_tokens idempotency_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.idempotency_tokens
    ADD CONSTRAINT idempotency_tokens_pkey PRIMARY KEY (id);


--
-- Name: inbox_webhooks inbox_webhooks_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.inbox_webhooks
    ADD CONSTRAINT inbox_webhooks_pkey PRIMARY KEY (id);


--
-- Name: internal_wallets internal_wallets_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.internal_wallets
    ADD CONSTRAINT internal_wallets_pkey PRIMARY KEY (id);


--
-- Name: notification_activities notification_activities_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.notification_activities
    ADD CONSTRAINT notification_activities_pkey PRIMARY KEY (id);


--
-- Name: notification_preferences notification_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.notification_preferences
    ADD CONSTRAINT notification_preferences_pkey PRIMARY KEY (id);


--
-- Name: notification_queue notification_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.notification_queue
    ADD CONSTRAINT notification_queue_pkey PRIMARY KEY (id);


--
-- Name: onboarding_sessions onboarding_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.onboarding_sessions
    ADD CONSTRAINT onboarding_sessions_pkey PRIMARY KEY (id);


--
-- Name: otp_verifications otp_verifications_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.otp_verifications
    ADD CONSTRAINT otp_verifications_pkey PRIMARY KEY (id);


--
-- Name: outbox_events outbox_events_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.outbox_events
    ADD CONSTRAINT outbox_events_pkey PRIMARY KEY (id);


--
-- Name: payment_addresses payment_addresses_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.payment_addresses
    ADD CONSTRAINT payment_addresses_pkey PRIMARY KEY (id);


--
-- Name: pending_cashouts pending_cashouts_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pending_cashouts
    ADD CONSTRAINT pending_cashouts_pkey PRIMARY KEY (id);


--
-- Name: platform_revenue platform_revenue_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.platform_revenue
    ADD CONSTRAINT platform_revenue_pkey PRIMARY KEY (id);


--
-- Name: ratings ratings_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ratings
    ADD CONSTRAINT ratings_pkey PRIMARY KEY (id);


--
-- Name: refunds refunds_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.refunds
    ADD CONSTRAINT refunds_pkey PRIMARY KEY (id);


--
-- Name: saga_steps saga_steps_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.saga_steps
    ADD CONSTRAINT saga_steps_pkey PRIMARY KEY (id);


--
-- Name: saved_addresses saved_addresses_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.saved_addresses
    ADD CONSTRAINT saved_addresses_pkey PRIMARY KEY (id);


--
-- Name: saved_bank_accounts saved_bank_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.saved_bank_accounts
    ADD CONSTRAINT saved_bank_accounts_pkey PRIMARY KEY (id);


--
-- Name: security_audits security_audits_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.security_audits
    ADD CONSTRAINT security_audits_pkey PRIMARY KEY (id);


--
-- Name: support_messages support_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.support_messages
    ADD CONSTRAINT support_messages_pkey PRIMARY KEY (id);


--
-- Name: support_tickets support_tickets_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.support_tickets
    ADD CONSTRAINT support_tickets_pkey PRIMARY KEY (id);


--
-- Name: support_tickets support_tickets_ticket_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.support_tickets
    ADD CONSTRAINT support_tickets_ticket_id_key UNIQUE (ticket_id);


--
-- Name: system_config system_config_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.system_config
    ADD CONSTRAINT system_config_pkey PRIMARY KEY (key);


--
-- Name: transaction_engine_events transaction_engine_events_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.transaction_engine_events
    ADD CONSTRAINT transaction_engine_events_pkey PRIMARY KEY (id);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: transactions transactions_utid_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_utid_key UNIQUE (utid);


--
-- Name: unified_transaction_retry_logs unified_transaction_retry_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.unified_transaction_retry_logs
    ADD CONSTRAINT unified_transaction_retry_logs_pkey PRIMARY KEY (id);


--
-- Name: unified_transaction_status_history unified_transaction_status_history_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.unified_transaction_status_history
    ADD CONSTRAINT unified_transaction_status_history_pkey PRIMARY KEY (id);


--
-- Name: unified_transactions unified_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.unified_transactions
    ADD CONSTRAINT unified_transactions_pkey PRIMARY KEY (id);


--
-- Name: escrow_refund_operations uq_escrow_refund_dedup; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrow_refund_operations
    ADD CONSTRAINT uq_escrow_refund_dedup UNIQUE (escrow_id, buyer_id, refund_cycle_id);


--
-- Name: escrow_refund_operations uq_escrow_refund_reason; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrow_refund_operations
    ADD CONSTRAINT uq_escrow_refund_reason UNIQUE (escrow_id, refund_reason);


--
-- Name: otp_verifications uq_otp_user_type; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.otp_verifications
    ADD CONSTRAINT uq_otp_user_type UNIQUE (user_id, verification_type);


--
-- Name: internal_wallets uq_provider_currency; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.internal_wallets
    ADD CONSTRAINT uq_provider_currency UNIQUE (provider_name, currency);


--
-- Name: saved_bank_accounts uq_user_account; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.saved_bank_accounts
    ADD CONSTRAINT uq_user_account UNIQUE (user_id, account_number);


--
-- Name: saved_addresses uq_user_address; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.saved_addresses
    ADD CONSTRAINT uq_user_address UNIQUE (user_id, address);


--
-- Name: wallets uq_user_currency; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT uq_user_currency UNIQUE (user_id, currency);


--
-- Name: notification_preferences uq_user_notification_pref; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.notification_preferences
    ADD CONSTRAINT uq_user_notification_pref UNIQUE (user_id);


--
-- Name: user_sms_usage uq_user_sms_usage_daily; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_sms_usage
    ADD CONSTRAINT uq_user_sms_usage_daily UNIQUE (user_id, date);


--
-- Name: webhook_event_ledger uq_webhook_event_provider_id; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.webhook_event_ledger
    ADD CONSTRAINT uq_webhook_event_provider_id UNIQUE (event_provider, event_id);


--
-- Name: user_achievements user_achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_pkey PRIMARY KEY (id);


--
-- Name: user_contacts user_contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_contacts
    ADD CONSTRAINT user_contacts_pkey PRIMARY KEY (id);


--
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (session_id);


--
-- Name: user_sms_usage user_sms_usage_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_sms_usage
    ADD CONSTRAINT user_sms_usage_pkey PRIMARY KEY (id);


--
-- Name: user_streak_tracking user_streak_tracking_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_streak_tracking
    ADD CONSTRAINT user_streak_tracking_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_profile_slug_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_profile_slug_key UNIQUE (profile_slug);


--
-- Name: wallet_balance_snapshots wallet_balance_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallet_balance_snapshots
    ADD CONSTRAINT wallet_balance_snapshots_pkey PRIMARY KEY (id);


--
-- Name: wallet_holds wallet_holds_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallet_holds
    ADD CONSTRAINT wallet_holds_pkey PRIMARY KEY (id);


--
-- Name: wallets wallets_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_pkey PRIMARY KEY (id);


--
-- Name: wallets wallets_utid_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_utid_key UNIQUE (utid);


--
-- Name: webhook_event_ledger webhook_event_ledger_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.webhook_event_ledger
    ADD CONSTRAINT webhook_event_ledger_pkey PRIMARY KEY (id);


--
-- Name: idx_replit_database_migrations_v1_build_id; Type: INDEX; Schema: _system; Owner: neondb_owner
--

CREATE UNIQUE INDEX idx_replit_database_migrations_v1_build_id ON _system.replit_database_migrations_v1 USING btree (build_id);


--
-- Name: idx_admin_override_active; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_admin_override_active ON public.admin_operation_overrides USING btree (provider, operation_type, is_active);


--
-- Name: idx_admin_override_expires; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_admin_override_expires ON public.admin_operation_overrides USING btree (expires_at);


--
-- Name: idx_audit_event_entity; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_audit_event_entity ON public.audit_events USING btree (entity_type, entity_id);


--
-- Name: idx_audit_event_processed; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_audit_event_processed ON public.audit_events USING btree (processed);


--
-- Name: idx_audit_event_timestamp; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_audit_event_timestamp ON public.audit_events USING btree (created_at);


--
-- Name: idx_audit_event_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_audit_event_type ON public.audit_events USING btree (event_type);


--
-- Name: idx_balance_alert_state_alert_key; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_balance_alert_state_alert_key ON public.balance_alert_state USING btree (alert_key);


--
-- Name: idx_balance_alert_state_alert_level; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_balance_alert_state_alert_level ON public.balance_alert_state USING btree (alert_level);


--
-- Name: idx_balance_alert_state_currency; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_balance_alert_state_currency ON public.balance_alert_state USING btree (currency);


--
-- Name: idx_balance_alert_state_last_alert; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_balance_alert_state_last_alert ON public.balance_alert_state USING btree (last_alert_time);


--
-- Name: idx_balance_alert_state_provider; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_balance_alert_state_provider ON public.balance_alert_state USING btree (provider);


--
-- Name: idx_balance_alert_state_provider_currency; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_balance_alert_state_provider_currency ON public.balance_alert_state USING btree (provider, currency);


--
-- Name: idx_balance_audit_change_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_balance_audit_change_type ON public.balance_audit_logs USING btree (change_type, currency, created_at);


--
-- Name: idx_balance_audit_operation_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_balance_audit_operation_type ON public.balance_audit_logs USING btree (operation_type, created_at);


--
-- Name: idx_balance_audit_transaction; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_balance_audit_transaction ON public.balance_audit_logs USING btree (transaction_id, transaction_type);


--
-- Name: idx_balance_audit_user_currency_time; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_balance_audit_user_currency_time ON public.balance_audit_logs USING btree (user_id, currency, created_at);


--
-- Name: idx_balance_audit_validation; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_balance_audit_validation ON public.balance_audit_logs USING btree (balance_validation_passed, created_at);


--
-- Name: idx_balance_audit_wallet_time; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_balance_audit_wallet_time ON public.balance_audit_logs USING btree (wallet_type, wallet_id, created_at);


--
-- Name: idx_balance_log_allowed; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_balance_log_allowed ON public.balance_protection_logs USING btree (operation_allowed, created_at);


--
-- Name: idx_balance_log_operation; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_balance_log_operation ON public.balance_protection_logs USING btree (operation_type, currency);


--
-- Name: idx_balance_log_user; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_balance_log_user ON public.balance_protection_logs USING btree (user_id, created_at);


--
-- Name: idx_cashouts_bank_account_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_cashouts_bank_account_id ON public.cashouts USING btree (bank_account_id) WHERE (bank_account_id IS NOT NULL);


--
-- Name: idx_cashouts_destination; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_cashouts_destination ON public.cashouts USING btree (destination) WHERE (destination IS NOT NULL);


--
-- Name: idx_cashouts_external_tx_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_cashouts_external_tx_id ON public.cashouts USING btree (external_tx_id) WHERE (external_tx_id IS NOT NULL);


--
-- Name: idx_cashouts_fincra_request_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_cashouts_fincra_request_id ON public.cashouts USING btree (fincra_request_id) WHERE (fincra_request_id IS NOT NULL);


--
-- Name: idx_cashouts_utid; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_cashouts_utid ON public.cashouts USING btree (utid);


--
-- Name: idx_crypto_deposit_status_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_crypto_deposit_status_created ON public.crypto_deposits USING btree (status, created_at);


--
-- Name: idx_crypto_deposit_txid_provider; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_crypto_deposit_txid_provider ON public.crypto_deposits USING btree (txid, provider);


--
-- Name: idx_crypto_deposit_user_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_crypto_deposit_user_status ON public.crypto_deposits USING btree (user_id, status);


--
-- Name: idx_email_verifications_active_records; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_email_verifications_active_records ON public.email_verifications USING btree (deleted_at) WHERE (deleted_at IS NULL);


--
-- Name: idx_email_verifications_active_unverified_unique; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX idx_email_verifications_active_unverified_unique ON public.email_verifications USING btree (email, purpose) WHERE ((deleted_at IS NULL) AND (verified = false));


--
-- Name: INDEX idx_email_verifications_active_unverified_unique; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON INDEX public.idx_email_verifications_active_unverified_unique IS 'Ensures only one active unverified verification record per email+purpose combination';


--
-- Name: idx_escrow_refund_ops_buyer; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_escrow_refund_ops_buyer ON public.escrow_refund_operations USING btree (buyer_id);


--
-- Name: idx_escrow_refund_ops_escrow; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_escrow_refund_ops_escrow ON public.escrow_refund_operations USING btree (escrow_id);


--
-- Name: idx_escrow_refund_ops_reason; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_escrow_refund_ops_reason ON public.escrow_refund_operations USING btree (refund_reason);


--
-- Name: idx_escrow_refund_ops_status_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_escrow_refund_ops_status_created ON public.escrow_refund_operations USING btree (status, created_at);


--
-- Name: idx_internal_wallet_balance; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_internal_wallet_balance ON public.internal_wallets USING btree (available_balance, currency);


--
-- Name: idx_internal_wallet_currency; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_internal_wallet_currency ON public.internal_wallets USING btree (currency, is_active);


--
-- Name: idx_internal_wallet_provider; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_internal_wallet_provider ON public.internal_wallets USING btree (provider_name, is_active);


--
-- Name: idx_onboarding_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_onboarding_created ON public.onboarding_sessions USING btree (created_at);


--
-- Name: idx_onboarding_email; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_onboarding_email ON public.onboarding_sessions USING btree (email);


--
-- Name: idx_onboarding_expires; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_onboarding_expires ON public.onboarding_sessions USING btree (expires_at);


--
-- Name: idx_onboarding_step; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_onboarding_step ON public.onboarding_sessions USING btree (current_step);


--
-- Name: idx_onboarding_user; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_onboarding_user ON public.onboarding_sessions USING btree (user_id);


--
-- Name: idx_pending_cashout_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_pending_cashout_created ON public.pending_cashouts USING btree (created_at);


--
-- Name: idx_pending_cashout_expires; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_pending_cashout_expires ON public.pending_cashouts USING btree (expires_at);


--
-- Name: idx_pending_cashout_user; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_pending_cashout_user ON public.pending_cashouts USING btree (user_id);


--
-- Name: idx_reconciliation_currency_time; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_reconciliation_currency_time ON public.balance_reconciliation_logs USING btree (currency, started_at);


--
-- Name: idx_reconciliation_discrepancies; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_reconciliation_discrepancies ON public.balance_reconciliation_logs USING btree (discrepancies_found, started_at);


--
-- Name: idx_reconciliation_status_time; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_reconciliation_status_time ON public.balance_reconciliation_logs USING btree (status, started_at);


--
-- Name: idx_reconciliation_type_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_reconciliation_type_status ON public.balance_reconciliation_logs USING btree (reconciliation_type, status);


--
-- Name: idx_reconciliation_user_time; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_reconciliation_user_time ON public.balance_reconciliation_logs USING btree (user_id, started_at);


--
-- Name: idx_refund_cashout; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_refund_cashout ON public.refunds USING btree (cashout_id);


--
-- Name: idx_refund_idempotency; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_refund_idempotency ON public.refunds USING btree (idempotency_key);


--
-- Name: idx_refund_status_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_refund_status_created ON public.refunds USING btree (status, created_at);


--
-- Name: idx_refund_user_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_refund_user_type ON public.refunds USING btree (user_id, refund_type);


--
-- Name: idx_saved_address_active; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_saved_address_active ON public.saved_addresses USING btree (is_active);


--
-- Name: idx_saved_address_user_currency; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_saved_address_user_currency ON public.saved_addresses USING btree (user_id, currency);


--
-- Name: idx_saved_bank_active; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_saved_bank_active ON public.saved_bank_accounts USING btree (is_active);


--
-- Name: idx_saved_bank_default; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_saved_bank_default ON public.saved_bank_accounts USING btree (user_id, is_default);


--
-- Name: idx_saved_bank_user; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_saved_bank_user ON public.saved_bank_accounts USING btree (user_id);


--
-- Name: idx_snapshot_type_time; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_snapshot_type_time ON public.wallet_balance_snapshots USING btree (snapshot_type, created_at);


--
-- Name: idx_snapshot_user_currency_time; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_snapshot_user_currency_time ON public.wallet_balance_snapshots USING btree (user_id, currency, created_at);


--
-- Name: idx_snapshot_validation; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_snapshot_validation ON public.wallet_balance_snapshots USING btree (validation_passed, created_at);


--
-- Name: idx_snapshot_wallet_time; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_snapshot_wallet_time ON public.wallet_balance_snapshots USING btree (wallet_type, wallet_id, created_at);


--
-- Name: idx_transactions_utid; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_transactions_utid ON public.transactions USING btree (utid);


--
-- Name: idx_unified_retry_error_code; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_unified_retry_error_code ON public.unified_transaction_retry_logs USING btree (error_code, attempted_at);


--
-- Name: idx_unified_retry_final; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_unified_retry_final ON public.unified_transaction_retry_logs USING btree (final_retry, attempted_at);


--
-- Name: idx_unified_retry_next; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_unified_retry_next ON public.unified_transaction_retry_logs USING btree (next_retry_at);


--
-- Name: idx_unified_retry_provider; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_unified_retry_provider ON public.unified_transaction_retry_logs USING btree (external_provider, attempted_at);


--
-- Name: idx_unified_retry_transaction; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_unified_retry_transaction ON public.unified_transaction_retry_logs USING btree (transaction_id, retry_attempt);


--
-- Name: idx_user_achievements_achieved; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_user_achievements_achieved ON public.user_achievements USING btree (achieved, achieved_at);


--
-- Name: idx_user_achievements_user_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_user_achievements_user_type ON public.user_achievements USING btree (user_id, achievement_type);


--
-- Name: idx_user_sms_usage_date; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_user_sms_usage_date ON public.user_sms_usage USING btree (date);


--
-- Name: idx_user_sms_usage_user_date; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_user_sms_usage_user_date ON public.user_sms_usage USING btree (user_id, date);


--
-- Name: idx_user_streak_activity; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_user_streak_activity ON public.user_streak_tracking USING btree (daily_activity_streak, last_activity_date);


--
-- Name: idx_user_streak_user; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_user_streak_user ON public.user_streak_tracking USING btree (user_id);


--
-- Name: idx_users_cashout_preference; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_users_cashout_preference ON public.users USING btree (cashout_preference) WHERE (cashout_preference IS NOT NULL);


--
-- Name: idx_users_telegram_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_users_telegram_id ON public.users USING btree (telegram_id);


--
-- Name: idx_wallets_utid; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_wallets_utid ON public.wallets USING btree (utid);


--
-- Name: ix_admin_action_tokens_admin_email; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_admin_action_tokens_admin_email ON public.admin_action_tokens USING btree (admin_email);


--
-- Name: ix_admin_action_tokens_admin_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_admin_action_tokens_admin_user_id ON public.admin_action_tokens USING btree (admin_user_id);


--
-- Name: ix_admin_action_tokens_cashout_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_admin_action_tokens_cashout_id ON public.admin_action_tokens USING btree (cashout_id);


--
-- Name: ix_admin_action_tokens_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_admin_action_tokens_created ON public.admin_action_tokens USING btree (created_at);


--
-- Name: ix_admin_action_tokens_expires; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_admin_action_tokens_expires ON public.admin_action_tokens USING btree (expires_at);


--
-- Name: ix_admin_action_tokens_token; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_admin_action_tokens_token ON public.admin_action_tokens USING btree (token);


--
-- Name: ix_admin_operation_overrides_expires_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_admin_operation_overrides_expires_at ON public.admin_operation_overrides USING btree (expires_at);


--
-- Name: ix_admin_operation_overrides_is_active; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_admin_operation_overrides_is_active ON public.admin_operation_overrides USING btree (is_active);


--
-- Name: ix_admin_operation_overrides_operation_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_admin_operation_overrides_operation_type ON public.admin_operation_overrides USING btree (operation_type);


--
-- Name: ix_admin_operation_overrides_provider; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_admin_operation_overrides_provider ON public.admin_operation_overrides USING btree (provider);


--
-- Name: ix_audit_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_audit_created ON public.audit_logs USING btree (created_at);


--
-- Name: ix_audit_entity_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_audit_entity_id ON public.audit_logs USING btree (entity_type, entity_id);


--
-- Name: ix_audit_event_entity; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_audit_event_entity ON public.audit_logs USING btree (event_type, entity_type);


--
-- Name: ix_audit_events_event_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_audit_events_event_id ON public.audit_events USING btree (event_id);


--
-- Name: ix_audit_events_processed; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_audit_events_processed ON public.audit_events USING btree (processed);


--
-- Name: ix_audit_events_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_audit_events_user_id ON public.audit_events USING btree (user_id);


--
-- Name: ix_audit_logs_admin_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_audit_logs_admin_id ON public.audit_logs USING btree (admin_id);


--
-- Name: ix_audit_logs_event_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_audit_logs_event_type ON public.audit_logs USING btree (event_type);


--
-- Name: ix_audit_logs_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_audit_logs_user_id ON public.audit_logs USING btree (user_id);


--
-- Name: ix_audit_user_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_audit_user_created ON public.audit_logs USING btree (user_id, created_at);


--
-- Name: ix_balance_audit_logs_audit_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_balance_audit_logs_audit_id ON public.balance_audit_logs USING btree (audit_id);


--
-- Name: ix_balance_audit_logs_cashout_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_audit_logs_cashout_id ON public.balance_audit_logs USING btree (cashout_id);


--
-- Name: ix_balance_audit_logs_created_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_audit_logs_created_at ON public.balance_audit_logs USING btree (created_at);


--
-- Name: ix_balance_audit_logs_currency; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_audit_logs_currency ON public.balance_audit_logs USING btree (currency);


--
-- Name: ix_balance_audit_logs_escrow_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_audit_logs_escrow_id ON public.balance_audit_logs USING btree (escrow_id);


--
-- Name: ix_balance_audit_logs_escrow_pk; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_audit_logs_escrow_pk ON public.balance_audit_logs USING btree (escrow_pk);


--
-- Name: ix_balance_audit_logs_exchange_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_audit_logs_exchange_id ON public.balance_audit_logs USING btree (exchange_id);


--
-- Name: ix_balance_audit_logs_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_audit_logs_id ON public.balance_audit_logs USING btree (id);


--
-- Name: ix_balance_audit_logs_idempotency_key; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_audit_logs_idempotency_key ON public.balance_audit_logs USING btree (idempotency_key);


--
-- Name: ix_balance_audit_logs_internal_wallet_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_audit_logs_internal_wallet_id ON public.balance_audit_logs USING btree (internal_wallet_id);


--
-- Name: ix_balance_audit_logs_operation_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_audit_logs_operation_type ON public.balance_audit_logs USING btree (operation_type);


--
-- Name: ix_balance_audit_logs_transaction_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_audit_logs_transaction_id ON public.balance_audit_logs USING btree (transaction_id);


--
-- Name: ix_balance_audit_logs_transaction_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_audit_logs_transaction_type ON public.balance_audit_logs USING btree (transaction_type);


--
-- Name: ix_balance_audit_logs_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_audit_logs_user_id ON public.balance_audit_logs USING btree (user_id);


--
-- Name: ix_balance_audit_logs_wallet_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_audit_logs_wallet_id ON public.balance_audit_logs USING btree (wallet_id);


--
-- Name: ix_balance_audit_logs_wallet_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_audit_logs_wallet_type ON public.balance_audit_logs USING btree (wallet_type);


--
-- Name: ix_balance_protection_logs_created_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_protection_logs_created_at ON public.balance_protection_logs USING btree (created_at);


--
-- Name: ix_balance_protection_logs_currency; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_protection_logs_currency ON public.balance_protection_logs USING btree (currency);


--
-- Name: ix_balance_protection_logs_operation_allowed; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_protection_logs_operation_allowed ON public.balance_protection_logs USING btree (operation_allowed);


--
-- Name: ix_balance_protection_logs_operation_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_protection_logs_operation_type ON public.balance_protection_logs USING btree (operation_type);


--
-- Name: ix_balance_protection_logs_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_protection_logs_user_id ON public.balance_protection_logs USING btree (user_id);


--
-- Name: ix_balance_reconciliation_logs_completed_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_reconciliation_logs_completed_at ON public.balance_reconciliation_logs USING btree (completed_at);


--
-- Name: ix_balance_reconciliation_logs_currency; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_reconciliation_logs_currency ON public.balance_reconciliation_logs USING btree (currency);


--
-- Name: ix_balance_reconciliation_logs_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_reconciliation_logs_id ON public.balance_reconciliation_logs USING btree (id);


--
-- Name: ix_balance_reconciliation_logs_internal_wallet_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_reconciliation_logs_internal_wallet_id ON public.balance_reconciliation_logs USING btree (internal_wallet_id);


--
-- Name: ix_balance_reconciliation_logs_reconciliation_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_balance_reconciliation_logs_reconciliation_id ON public.balance_reconciliation_logs USING btree (reconciliation_id);


--
-- Name: ix_balance_reconciliation_logs_reconciliation_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_reconciliation_logs_reconciliation_type ON public.balance_reconciliation_logs USING btree (reconciliation_type);


--
-- Name: ix_balance_reconciliation_logs_started_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_reconciliation_logs_started_at ON public.balance_reconciliation_logs USING btree (started_at);


--
-- Name: ix_balance_reconciliation_logs_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_reconciliation_logs_status ON public.balance_reconciliation_logs USING btree (status);


--
-- Name: ix_balance_reconciliation_logs_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_balance_reconciliation_logs_user_id ON public.balance_reconciliation_logs USING btree (user_id);


--
-- Name: ix_cashouts_admin_approval; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_cashouts_admin_approval ON public.cashouts USING btree (admin_approved, status);


--
-- Name: ix_cashouts_cashout_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_cashouts_cashout_id ON public.cashouts USING btree (cashout_id);


--
-- Name: ix_cashouts_status_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_cashouts_status_created ON public.cashouts USING btree (status, created_at);


--
-- Name: ix_cashouts_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_cashouts_user_id ON public.cashouts USING btree (user_id);


--
-- Name: ix_cashouts_user_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_cashouts_user_status ON public.cashouts USING btree (user_id, status);


--
-- Name: ix_crypto_deposits_order_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_crypto_deposits_order_id ON public.crypto_deposits USING btree (order_id);


--
-- Name: ix_crypto_deposits_provider; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_crypto_deposits_provider ON public.crypto_deposits USING btree (provider);


--
-- Name: ix_crypto_deposits_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_crypto_deposits_status ON public.crypto_deposits USING btree (status);


--
-- Name: ix_crypto_deposits_txid; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_crypto_deposits_txid ON public.crypto_deposits USING btree (txid);


--
-- Name: ix_crypto_deposits_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_crypto_deposits_user_id ON public.crypto_deposits USING btree (user_id);


--
-- Name: ix_dispute_messages_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_dispute_messages_created ON public.dispute_messages USING btree (created_at);


--
-- Name: ix_dispute_messages_dispute; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_dispute_messages_dispute ON public.dispute_messages USING btree (dispute_id);


--
-- Name: ix_dispute_messages_sender; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_dispute_messages_sender ON public.dispute_messages USING btree (sender_id);


--
-- Name: ix_disputes_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_disputes_created ON public.disputes USING btree (created_at);


--
-- Name: ix_disputes_escrow; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_disputes_escrow ON public.disputes USING btree (escrow_id);


--
-- Name: ix_disputes_initiator; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_disputes_initiator ON public.disputes USING btree (initiator_id);


--
-- Name: ix_disputes_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_disputes_status ON public.disputes USING btree (status);


--
-- Name: ix_distributed_locks_expires_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_distributed_locks_expires_at ON public.distributed_locks USING btree (expires_at);


--
-- Name: ix_distributed_locks_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_distributed_locks_id ON public.distributed_locks USING btree (id);


--
-- Name: ix_distributed_locks_lock_name; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_distributed_locks_lock_name ON public.distributed_locks USING btree (lock_name);


--
-- Name: ix_email_verifications_code; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_email_verifications_code ON public.email_verifications USING btree (verification_code);


--
-- Name: ix_email_verifications_expires; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_email_verifications_expires ON public.email_verifications USING btree (expires_at);


--
-- Name: ix_email_verifications_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_email_verifications_user_id ON public.email_verifications USING btree (user_id);


--
-- Name: ix_email_verifications_user_purpose; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_email_verifications_user_purpose ON public.email_verifications USING btree (user_id, purpose);


--
-- Name: ix_escrow_holdings_escrow_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrow_holdings_escrow_id ON public.escrow_holdings USING btree (escrow_id);


--
-- Name: ix_escrow_messages_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrow_messages_created ON public.escrow_messages USING btree (created_at);


--
-- Name: ix_escrow_messages_escrow; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrow_messages_escrow ON public.escrow_messages USING btree (escrow_id);


--
-- Name: ix_escrow_messages_sender; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrow_messages_sender ON public.escrow_messages USING btree (sender_id);


--
-- Name: ix_escrow_refund_operations_buyer_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrow_refund_operations_buyer_id ON public.escrow_refund_operations USING btree (buyer_id);


--
-- Name: ix_escrow_refund_operations_escrow_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrow_refund_operations_escrow_id ON public.escrow_refund_operations USING btree (escrow_id);


--
-- Name: ix_escrow_refund_operations_idempotency_key; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrow_refund_operations_idempotency_key ON public.escrow_refund_operations USING btree (idempotency_key);


--
-- Name: ix_escrows_auto_release; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrows_auto_release ON public.escrows USING btree (auto_release_at);


--
-- Name: ix_escrows_buyer_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrows_buyer_id ON public.escrows USING btree (buyer_id);


--
-- Name: ix_escrows_buyer_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrows_buyer_status ON public.escrows USING btree (buyer_id, status);


--
-- Name: ix_escrows_contact_email; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrows_contact_email ON public.escrows USING btree (seller_contact_value) WHERE ((seller_contact_type)::text = 'email'::text);


--
-- Name: ix_escrows_contact_phone; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrows_contact_phone ON public.escrows USING btree (seller_contact_value) WHERE ((seller_contact_type)::text = 'phone'::text);


--
-- Name: ix_escrows_contact_username; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrows_contact_username ON public.escrows USING btree (seller_contact_value) WHERE ((seller_contact_type)::text = 'username'::text);


--
-- Name: ix_escrows_delivery_deadline; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrows_delivery_deadline ON public.escrows USING btree (delivery_deadline);


--
-- Name: ix_escrows_escrow_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_escrows_escrow_id ON public.escrows USING btree (escrow_id);


--
-- Name: ix_escrows_expires_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrows_expires_at ON public.escrows USING btree (expires_at);


--
-- Name: ix_escrows_seller_email_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrows_seller_email_status ON public.escrows USING btree (seller_email, status) WHERE (seller_email IS NOT NULL);


--
-- Name: ix_escrows_seller_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrows_seller_id ON public.escrows USING btree (seller_id);


--
-- Name: ix_escrows_seller_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrows_seller_status ON public.escrows USING btree (seller_id, status);


--
-- Name: ix_escrows_status_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_escrows_status_created ON public.escrows USING btree (status, created_at);


--
-- Name: ix_escrows_utid; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_escrows_utid ON public.escrows USING btree (utid);


--
-- Name: ix_exchange_orders_exchange_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_exchange_orders_exchange_id ON public.exchange_orders USING btree (exchange_id);


--
-- Name: ix_exchange_orders_user; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_exchange_orders_user ON public.exchange_orders USING btree (user_id);


--
-- Name: ix_exchange_orders_utid; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_exchange_orders_utid ON public.exchange_orders USING btree (utid);


--
-- Name: ix_idempotency_keys_expires; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_idempotency_keys_expires ON public.idempotency_keys USING btree (expires_at);


--
-- Name: ix_idempotency_keys_operation_key; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_idempotency_keys_operation_key ON public.idempotency_keys USING btree (operation_key);


--
-- Name: ix_idempotency_keys_operation_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_idempotency_keys_operation_type ON public.idempotency_keys USING btree (operation_type);


--
-- Name: ix_idempotency_keys_user; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_idempotency_keys_user ON public.idempotency_keys USING btree (user_id);


--
-- Name: ix_idempotency_tokens_expires_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_idempotency_tokens_expires_at ON public.idempotency_tokens USING btree (expires_at);


--
-- Name: ix_idempotency_tokens_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_idempotency_tokens_id ON public.idempotency_tokens USING btree (id);


--
-- Name: ix_idempotency_tokens_idempotency_key; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_idempotency_tokens_idempotency_key ON public.idempotency_tokens USING btree (idempotency_key);


--
-- Name: ix_idempotency_tokens_operation_resource; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_idempotency_tokens_operation_resource ON public.idempotency_tokens USING btree (operation_type, resource_id);


--
-- Name: ix_idempotency_tokens_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_idempotency_tokens_status ON public.idempotency_tokens USING btree (status);


--
-- Name: ix_inbox_webhooks_event_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_inbox_webhooks_event_type ON public.inbox_webhooks USING btree (event_type);


--
-- Name: ix_inbox_webhooks_provider; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_inbox_webhooks_provider ON public.inbox_webhooks USING btree (provider);


--
-- Name: ix_inbox_webhooks_provider_event; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_inbox_webhooks_provider_event ON public.inbox_webhooks USING btree (provider, event_type);


--
-- Name: ix_inbox_webhooks_received_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_inbox_webhooks_received_at ON public.inbox_webhooks USING btree (first_received_at);


--
-- Name: ix_inbox_webhooks_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_inbox_webhooks_status ON public.inbox_webhooks USING btree (status);


--
-- Name: ix_inbox_webhooks_transaction; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_inbox_webhooks_transaction ON public.inbox_webhooks USING btree (transaction_id);


--
-- Name: ix_inbox_webhooks_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_inbox_webhooks_user_id ON public.inbox_webhooks USING btree (user_id);


--
-- Name: ix_inbox_webhooks_webhook_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_inbox_webhooks_webhook_id ON public.inbox_webhooks USING btree (webhook_id);


--
-- Name: ix_internal_wallets_currency; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_internal_wallets_currency ON public.internal_wallets USING btree (currency);


--
-- Name: ix_internal_wallets_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_internal_wallets_id ON public.internal_wallets USING btree (id);


--
-- Name: ix_internal_wallets_provider_name; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_internal_wallets_provider_name ON public.internal_wallets USING btree (provider_name);


--
-- Name: ix_internal_wallets_wallet_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_internal_wallets_wallet_id ON public.internal_wallets USING btree (wallet_id);


--
-- Name: ix_notification_activities_activity_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_notification_activities_activity_id ON public.notification_activities USING btree (activity_id);


--
-- Name: ix_notification_activities_channel_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_notification_activities_channel_type ON public.notification_activities USING btree (channel_type);


--
-- Name: ix_notification_activities_idempotency_key; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_notification_activities_idempotency_key ON public.notification_activities USING btree (idempotency_key);


--
-- Name: ix_notification_activities_notification_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_notification_activities_notification_type ON public.notification_activities USING btree (notification_type);


--
-- Name: ix_notification_queue_idempotency_key; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_notification_queue_idempotency_key ON public.notification_queue USING btree (idempotency_key);


--
-- Name: ix_notification_queue_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_notification_queue_user_id ON public.notification_queue USING btree (user_id);


--
-- Name: ix_notifications_scheduled; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_notifications_scheduled ON public.notification_queue USING btree (scheduled_at);


--
-- Name: ix_notifications_status_priority; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_notifications_status_priority ON public.notification_queue USING btree (status, priority);


--
-- Name: ix_notifications_user_channel; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_notifications_user_channel ON public.notification_queue USING btree (user_id, channel);


--
-- Name: ix_onboarding_sessions_current_step; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_onboarding_sessions_current_step ON public.onboarding_sessions USING btree (current_step);


--
-- Name: ix_onboarding_sessions_email; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_onboarding_sessions_email ON public.onboarding_sessions USING btree (email);


--
-- Name: ix_onboarding_sessions_invite_token; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_onboarding_sessions_invite_token ON public.onboarding_sessions USING btree (invite_token);


--
-- Name: ix_onboarding_sessions_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_onboarding_sessions_user_id ON public.onboarding_sessions USING btree (user_id);


--
-- Name: ix_otp_verifications_expires; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_otp_verifications_expires ON public.otp_verifications USING btree (expires_at);


--
-- Name: ix_otp_verifications_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_otp_verifications_user_id ON public.otp_verifications USING btree (user_id);


--
-- Name: ix_otp_verifications_user_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_otp_verifications_user_type ON public.otp_verifications USING btree (user_id, verification_type);


--
-- Name: ix_outbox_events_aggregate_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_outbox_events_aggregate_id ON public.outbox_events USING btree (aggregate_id);


--
-- Name: ix_outbox_events_created_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_outbox_events_created_at ON public.outbox_events USING btree (created_at);


--
-- Name: ix_outbox_events_event_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_outbox_events_event_type ON public.outbox_events USING btree (event_type);


--
-- Name: ix_outbox_events_processed; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_outbox_events_processed ON public.outbox_events USING btree (processed);


--
-- Name: ix_payment_addresses_address; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_payment_addresses_address ON public.payment_addresses USING btree (address);


--
-- Name: ix_payment_addresses_currency_provider; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_payment_addresses_currency_provider ON public.payment_addresses USING btree (currency, provider);


--
-- Name: ix_payment_addresses_escrow_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_payment_addresses_escrow_id ON public.payment_addresses USING btree (escrow_id);


--
-- Name: ix_payment_addresses_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_payment_addresses_user_id ON public.payment_addresses USING btree (user_id);


--
-- Name: ix_payment_addresses_user_used; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_payment_addresses_user_used ON public.payment_addresses USING btree (user_id, is_used);


--
-- Name: ix_platform_revenue_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_platform_revenue_created ON public.platform_revenue USING btree (created_at);


--
-- Name: ix_platform_revenue_escrow; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_platform_revenue_escrow ON public.platform_revenue USING btree (escrow_id);


--
-- Name: ix_platform_revenue_fee_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_platform_revenue_fee_type ON public.platform_revenue USING btree (fee_type);


--
-- Name: ix_platform_revenue_source_transaction_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_platform_revenue_source_transaction_id ON public.platform_revenue USING btree (source_transaction_id);


--
-- Name: ix_ratings_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_ratings_created ON public.ratings USING btree (created_at);


--
-- Name: ix_ratings_escrow; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_ratings_escrow ON public.ratings USING btree (escrow_id);


--
-- Name: ix_ratings_rated; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_ratings_rated ON public.ratings USING btree (rated_id);


--
-- Name: ix_ratings_rater; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_ratings_rater ON public.ratings USING btree (rater_id);


--
-- Name: ix_refunds_idempotency_key; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_refunds_idempotency_key ON public.refunds USING btree (idempotency_key);


--
-- Name: ix_refunds_refund_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_refunds_refund_id ON public.refunds USING btree (refund_id);


--
-- Name: ix_refunds_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_refunds_status ON public.refunds USING btree (status);


--
-- Name: ix_saga_steps_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_saga_steps_created ON public.saga_steps USING btree (created_at);


--
-- Name: ix_saga_steps_saga_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_saga_steps_saga_id ON public.saga_steps USING btree (saga_id);


--
-- Name: ix_saga_steps_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_saga_steps_status ON public.saga_steps USING btree (status);


--
-- Name: ix_security_audits_action_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_security_audits_action_type ON public.security_audits USING btree (action_type);


--
-- Name: ix_security_audits_created_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_security_audits_created_at ON public.security_audits USING btree (created_at);


--
-- Name: ix_security_audits_risk_level; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_security_audits_risk_level ON public.security_audits USING btree (risk_level);


--
-- Name: ix_security_audits_user; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_security_audits_user ON public.security_audits USING btree (user_id);


--
-- Name: ix_support_messages_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_support_messages_created ON public.support_messages USING btree (created_at);


--
-- Name: ix_support_messages_sender; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_support_messages_sender ON public.support_messages USING btree (sender_id);


--
-- Name: ix_support_messages_ticket; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_support_messages_ticket ON public.support_messages USING btree (ticket_id);


--
-- Name: ix_support_tickets_assigned; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_support_tickets_assigned ON public.support_tickets USING btree (assigned_to);


--
-- Name: ix_support_tickets_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_support_tickets_created ON public.support_tickets USING btree (created_at);


--
-- Name: ix_support_tickets_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_support_tickets_status ON public.support_tickets USING btree (status);


--
-- Name: ix_support_tickets_user; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_support_tickets_user ON public.support_tickets USING btree (user_id);


--
-- Name: ix_system_config_public; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_system_config_public ON public.system_config USING btree (is_public);


--
-- Name: ix_transaction_engine_events_category; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transaction_engine_events_category ON public.transaction_engine_events USING btree (event_category);


--
-- Name: ix_transaction_engine_events_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transaction_engine_events_created ON public.transaction_engine_events USING btree (created_at);


--
-- Name: ix_transaction_engine_events_event_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_transaction_engine_events_event_id ON public.transaction_engine_events USING btree (event_id);


--
-- Name: ix_transaction_engine_events_event_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transaction_engine_events_event_type ON public.transaction_engine_events USING btree (event_type);


--
-- Name: ix_transaction_engine_events_saga_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transaction_engine_events_saga_id ON public.transaction_engine_events USING btree (saga_id);


--
-- Name: ix_transaction_engine_events_transaction; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transaction_engine_events_transaction ON public.transaction_engine_events USING btree (transaction_id);


--
-- Name: ix_transaction_engine_events_transaction_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transaction_engine_events_transaction_id ON public.transaction_engine_events USING btree (transaction_id);


--
-- Name: ix_transaction_engine_events_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transaction_engine_events_type ON public.transaction_engine_events USING btree (event_type);


--
-- Name: ix_transaction_engine_events_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transaction_engine_events_user_id ON public.transaction_engine_events USING btree (user_id);


--
-- Name: ix_transaction_status_history_changed_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transaction_status_history_changed_at ON public.unified_transaction_status_history USING btree (changed_at);


--
-- Name: ix_transaction_status_history_to_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transaction_status_history_to_status ON public.unified_transaction_status_history USING btree (to_status);


--
-- Name: ix_transaction_status_history_transaction; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transaction_status_history_transaction ON public.unified_transaction_status_history USING btree (transaction_id);


--
-- Name: ix_transactions_blockchain_hash; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transactions_blockchain_hash ON public.transactions USING btree (blockchain_tx_hash);


--
-- Name: ix_transactions_cashout_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transactions_cashout_id ON public.transactions USING btree (cashout_id);


--
-- Name: ix_transactions_escrow_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transactions_escrow_id ON public.transactions USING btree (escrow_id);


--
-- Name: ix_transactions_external_tx; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transactions_external_tx ON public.transactions USING btree (external_tx_id);


--
-- Name: ix_transactions_status_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transactions_status_created ON public.transactions USING btree (status, created_at);


--
-- Name: ix_transactions_transaction_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_transactions_transaction_id ON public.transactions USING btree (transaction_id);


--
-- Name: ix_transactions_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transactions_user_id ON public.transactions USING btree (user_id);


--
-- Name: ix_transactions_user_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_transactions_user_type ON public.transactions USING btree (user_id, transaction_type);


--
-- Name: ix_unified_transaction_retry_logs_error_code; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_unified_transaction_retry_logs_error_code ON public.unified_transaction_retry_logs USING btree (error_code);


--
-- Name: ix_unified_transaction_retry_logs_transaction_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_unified_transaction_retry_logs_transaction_id ON public.unified_transaction_retry_logs USING btree (transaction_id);


--
-- Name: ix_unified_transaction_status_history_transaction_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_unified_transaction_status_history_transaction_id ON public.unified_transaction_status_history USING btree (transaction_id);


--
-- Name: ix_unified_transactions_created_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_unified_transactions_created_at ON public.unified_transactions USING btree (created_at);


--
-- Name: ix_unified_transactions_external_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_unified_transactions_external_id ON public.unified_transactions USING btree (external_id);


--
-- Name: ix_unified_transactions_reference_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_unified_transactions_reference_id ON public.unified_transactions USING btree (reference_id);


--
-- Name: ix_unified_transactions_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_unified_transactions_status ON public.unified_transactions USING btree (status);


--
-- Name: ix_unified_transactions_transaction_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_unified_transactions_transaction_type ON public.unified_transactions USING btree (transaction_type);


--
-- Name: ix_unified_transactions_type_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_unified_transactions_type_status ON public.unified_transactions USING btree (transaction_type, status);


--
-- Name: ix_unified_transactions_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_unified_transactions_user_id ON public.unified_transactions USING btree (user_id);


--
-- Name: ix_unified_transactions_user_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_unified_transactions_user_status ON public.unified_transactions USING btree (user_id, status);


--
-- Name: ix_unique_escrow_overpayment; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_unique_escrow_overpayment ON public.transactions USING btree (user_id, escrow_id, transaction_type, amount, status) WHERE (((transaction_type)::text = 'escrow_overpayment'::text) AND ((status)::text = 'completed'::text));


--
-- Name: ix_user_achievements_achieved; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_user_achievements_achieved ON public.user_achievements USING btree (achieved);


--
-- Name: ix_user_achievements_achievement_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_user_achievements_achievement_type ON public.user_achievements USING btree (achievement_type);


--
-- Name: ix_user_achievements_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_user_achievements_user_id ON public.user_achievements USING btree (user_id);


--
-- Name: ix_user_contacts_contact_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_user_contacts_contact_id ON public.user_contacts USING btree (contact_id);


--
-- Name: ix_user_contacts_contact_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_user_contacts_contact_type ON public.user_contacts USING btree (contact_type);


--
-- Name: ix_user_contacts_contact_value; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_user_contacts_contact_value ON public.user_contacts USING btree (contact_value);


--
-- Name: ix_user_sessions_expires; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_user_sessions_expires ON public.user_sessions USING btree (expires_at);


--
-- Name: ix_user_sessions_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_user_sessions_user_id ON public.user_sessions USING btree (user_id);


--
-- Name: ix_user_sessions_user_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_user_sessions_user_type ON public.user_sessions USING btree (user_id, session_type);


--
-- Name: ix_user_sms_usage_date; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_user_sms_usage_date ON public.user_sms_usage USING btree (date);


--
-- Name: ix_user_sms_usage_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_user_sms_usage_user_id ON public.user_sms_usage USING btree (user_id);


--
-- Name: ix_user_streak_tracking_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_user_streak_tracking_user_id ON public.user_streak_tracking USING btree (user_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_phone_number; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_users_phone_number ON public.users USING btree (phone_number);


--
-- Name: ix_users_profile_slug; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_users_profile_slug ON public.users USING btree (profile_slug);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: ix_wallet_balance_snapshots_created_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_balance_snapshots_created_at ON public.wallet_balance_snapshots USING btree (created_at);


--
-- Name: ix_wallet_balance_snapshots_currency; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_balance_snapshots_currency ON public.wallet_balance_snapshots USING btree (currency);


--
-- Name: ix_wallet_balance_snapshots_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_balance_snapshots_id ON public.wallet_balance_snapshots USING btree (id);


--
-- Name: ix_wallet_balance_snapshots_internal_wallet_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_balance_snapshots_internal_wallet_id ON public.wallet_balance_snapshots USING btree (internal_wallet_id);


--
-- Name: ix_wallet_balance_snapshots_previous_snapshot_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_balance_snapshots_previous_snapshot_id ON public.wallet_balance_snapshots USING btree (previous_snapshot_id);


--
-- Name: ix_wallet_balance_snapshots_snapshot_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX ix_wallet_balance_snapshots_snapshot_id ON public.wallet_balance_snapshots USING btree (snapshot_id);


--
-- Name: ix_wallet_balance_snapshots_snapshot_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_balance_snapshots_snapshot_type ON public.wallet_balance_snapshots USING btree (snapshot_type);


--
-- Name: ix_wallet_balance_snapshots_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_balance_snapshots_user_id ON public.wallet_balance_snapshots USING btree (user_id);


--
-- Name: ix_wallet_balance_snapshots_valid_from; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_balance_snapshots_valid_from ON public.wallet_balance_snapshots USING btree (valid_from);


--
-- Name: ix_wallet_balance_snapshots_valid_until; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_balance_snapshots_valid_until ON public.wallet_balance_snapshots USING btree (valid_until);


--
-- Name: ix_wallet_balance_snapshots_wallet_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_balance_snapshots_wallet_id ON public.wallet_balance_snapshots USING btree (wallet_id);


--
-- Name: ix_wallet_balance_snapshots_wallet_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_balance_snapshots_wallet_type ON public.wallet_balance_snapshots USING btree (wallet_type);


--
-- Name: ix_wallet_holds_created; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_holds_created ON public.wallet_holds USING btree (created_at);


--
-- Name: ix_wallet_holds_reference; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_holds_reference ON public.wallet_holds USING btree (reference_id);


--
-- Name: ix_wallet_holds_reference_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_holds_reference_id ON public.wallet_holds USING btree (reference_id);


--
-- Name: ix_wallet_holds_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_holds_status ON public.wallet_holds USING btree (status);


--
-- Name: ix_wallet_holds_user; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallet_holds_user ON public.wallet_holds USING btree (user_id);


--
-- Name: ix_wallets_user_currency; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallets_user_currency ON public.wallets USING btree (user_id, currency);


--
-- Name: ix_wallets_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_wallets_user_id ON public.wallets USING btree (user_id);


--
-- Name: ix_webhook_event_ledger_created_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_webhook_event_ledger_created_status ON public.webhook_event_ledger USING btree (created_at, status);


--
-- Name: ix_webhook_event_ledger_event_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_webhook_event_ledger_event_id ON public.webhook_event_ledger USING btree (event_id);


--
-- Name: ix_webhook_event_ledger_event_provider; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_webhook_event_ledger_event_provider ON public.webhook_event_ledger USING btree (event_provider);


--
-- Name: ix_webhook_event_ledger_event_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_webhook_event_ledger_event_type ON public.webhook_event_ledger USING btree (event_type);


--
-- Name: ix_webhook_event_ledger_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_webhook_event_ledger_id ON public.webhook_event_ledger USING btree (id);


--
-- Name: ix_webhook_event_ledger_processed_at; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_webhook_event_ledger_processed_at ON public.webhook_event_ledger USING btree (processed_at);


--
-- Name: ix_webhook_event_ledger_provider_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_webhook_event_ledger_provider_status ON public.webhook_event_ledger USING btree (event_provider, status);


--
-- Name: ix_webhook_event_ledger_reference_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_webhook_event_ledger_reference_id ON public.webhook_event_ledger USING btree (reference_id);


--
-- Name: ix_webhook_event_ledger_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_webhook_event_ledger_status ON public.webhook_event_ledger USING btree (status);


--
-- Name: ix_webhook_event_ledger_txid; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_webhook_event_ledger_txid ON public.webhook_event_ledger USING btree (txid);


--
-- Name: ix_webhook_event_ledger_txid_reference; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_webhook_event_ledger_txid_reference ON public.webhook_event_ledger USING btree (txid, reference_id);


--
-- Name: ix_webhook_event_ledger_user_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_webhook_event_ledger_user_id ON public.webhook_event_ledger USING btree (user_id);


--
-- Name: ix_webhook_event_ledger_user_id_status; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX ix_webhook_event_ledger_user_id_status ON public.webhook_event_ledger USING btree (user_id, status);


--
-- Name: payment_addresses_utid_key; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX payment_addresses_utid_key ON public.payment_addresses USING btree (utid) WHERE (utid IS NOT NULL);


--
-- Name: balance_alert_state trigger_update_balance_alert_state_updated_at; Type: TRIGGER; Schema: public; Owner: neondb_owner
--

CREATE TRIGGER trigger_update_balance_alert_state_updated_at BEFORE UPDATE ON public.balance_alert_state FOR EACH ROW EXECUTE FUNCTION public.update_balance_alert_state_updated_at();


--
-- Name: audit_events audit_events_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: balance_audit_logs balance_audit_logs_escrow_pk_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.balance_audit_logs
    ADD CONSTRAINT balance_audit_logs_escrow_pk_fkey FOREIGN KEY (escrow_pk) REFERENCES public.escrows(id);


--
-- Name: balance_audit_logs balance_audit_logs_internal_wallet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.balance_audit_logs
    ADD CONSTRAINT balance_audit_logs_internal_wallet_id_fkey FOREIGN KEY (internal_wallet_id) REFERENCES public.internal_wallets(wallet_id);


--
-- Name: balance_audit_logs balance_audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.balance_audit_logs
    ADD CONSTRAINT balance_audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: balance_reconciliation_logs balance_reconciliation_logs_internal_wallet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.balance_reconciliation_logs
    ADD CONSTRAINT balance_reconciliation_logs_internal_wallet_id_fkey FOREIGN KEY (internal_wallet_id) REFERENCES public.internal_wallets(wallet_id);


--
-- Name: balance_reconciliation_logs balance_reconciliation_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.balance_reconciliation_logs
    ADD CONSTRAINT balance_reconciliation_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: cashouts cashouts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.cashouts
    ADD CONSTRAINT cashouts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: crypto_deposits crypto_deposits_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.crypto_deposits
    ADD CONSTRAINT crypto_deposits_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: dispute_messages dispute_messages_dispute_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.dispute_messages
    ADD CONSTRAINT dispute_messages_dispute_id_fkey FOREIGN KEY (dispute_id) REFERENCES public.disputes(id);


--
-- Name: dispute_messages dispute_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.dispute_messages
    ADD CONSTRAINT dispute_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id);


--
-- Name: disputes disputes_admin_assigned_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.disputes
    ADD CONSTRAINT disputes_admin_assigned_id_fkey FOREIGN KEY (admin_assigned_id) REFERENCES public.users(id);


--
-- Name: disputes disputes_escrow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.disputes
    ADD CONSTRAINT disputes_escrow_id_fkey FOREIGN KEY (escrow_id) REFERENCES public.escrows(id);


--
-- Name: disputes disputes_initiator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.disputes
    ADD CONSTRAINT disputes_initiator_id_fkey FOREIGN KEY (initiator_id) REFERENCES public.users(id);


--
-- Name: disputes disputes_respondent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.disputes
    ADD CONSTRAINT disputes_respondent_id_fkey FOREIGN KEY (respondent_id) REFERENCES public.users(id);


--
-- Name: email_verifications email_verifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.email_verifications
    ADD CONSTRAINT email_verifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: escrow_messages escrow_messages_escrow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrow_messages
    ADD CONSTRAINT escrow_messages_escrow_id_fkey FOREIGN KEY (escrow_id) REFERENCES public.escrows(id);


--
-- Name: escrow_messages escrow_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrow_messages
    ADD CONSTRAINT escrow_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id);


--
-- Name: escrow_refund_operations escrow_refund_operations_buyer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrow_refund_operations
    ADD CONSTRAINT escrow_refund_operations_buyer_id_fkey FOREIGN KEY (buyer_id) REFERENCES public.users(id);


--
-- Name: escrow_refund_operations escrow_refund_operations_escrow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrow_refund_operations
    ADD CONSTRAINT escrow_refund_operations_escrow_id_fkey FOREIGN KEY (escrow_id) REFERENCES public.escrows(id);


--
-- Name: escrows escrows_buyer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrows
    ADD CONSTRAINT escrows_buyer_id_fkey FOREIGN KEY (buyer_id) REFERENCES public.users(id);


--
-- Name: escrows escrows_seller_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.escrows
    ADD CONSTRAINT escrows_seller_id_fkey FOREIGN KEY (seller_id) REFERENCES public.users(id);


--
-- Name: exchange_orders exchange_orders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.exchange_orders
    ADD CONSTRAINT exchange_orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: idempotency_keys idempotency_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.idempotency_keys
    ADD CONSTRAINT idempotency_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: inbox_webhooks inbox_webhooks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.inbox_webhooks
    ADD CONSTRAINT inbox_webhooks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: notification_activities notification_activities_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.notification_activities
    ADD CONSTRAINT notification_activities_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: notification_preferences notification_preferences_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.notification_preferences
    ADD CONSTRAINT notification_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: notification_queue notification_queue_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.notification_queue
    ADD CONSTRAINT notification_queue_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: onboarding_sessions onboarding_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.onboarding_sessions
    ADD CONSTRAINT onboarding_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: otp_verifications otp_verifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.otp_verifications
    ADD CONSTRAINT otp_verifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: payment_addresses payment_addresses_escrow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.payment_addresses
    ADD CONSTRAINT payment_addresses_escrow_id_fkey FOREIGN KEY (escrow_id) REFERENCES public.escrows(id);


--
-- Name: payment_addresses payment_addresses_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.payment_addresses
    ADD CONSTRAINT payment_addresses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: pending_cashouts pending_cashouts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pending_cashouts
    ADD CONSTRAINT pending_cashouts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: ratings ratings_escrow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ratings
    ADD CONSTRAINT ratings_escrow_id_fkey FOREIGN KEY (escrow_id) REFERENCES public.escrows(id);


--
-- Name: ratings ratings_rated_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ratings
    ADD CONSTRAINT ratings_rated_id_fkey FOREIGN KEY (rated_id) REFERENCES public.users(id);


--
-- Name: ratings ratings_rater_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.ratings
    ADD CONSTRAINT ratings_rater_id_fkey FOREIGN KEY (rater_id) REFERENCES public.users(id);


--
-- Name: refunds refunds_admin_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.refunds
    ADD CONSTRAINT refunds_admin_approved_by_fkey FOREIGN KEY (admin_approved_by) REFERENCES public.users(id);


--
-- Name: refunds refunds_cashout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.refunds
    ADD CONSTRAINT refunds_cashout_id_fkey FOREIGN KEY (cashout_id) REFERENCES public.cashouts(cashout_id);


--
-- Name: refunds refunds_escrow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.refunds
    ADD CONSTRAINT refunds_escrow_id_fkey FOREIGN KEY (escrow_id) REFERENCES public.escrows(id);


--
-- Name: refunds refunds_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.refunds
    ADD CONSTRAINT refunds_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: saved_addresses saved_addresses_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.saved_addresses
    ADD CONSTRAINT saved_addresses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: saved_bank_accounts saved_bank_accounts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.saved_bank_accounts
    ADD CONSTRAINT saved_bank_accounts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: security_audits security_audits_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.security_audits
    ADD CONSTRAINT security_audits_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: support_messages support_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.support_messages
    ADD CONSTRAINT support_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id);


--
-- Name: support_messages support_messages_ticket_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.support_messages
    ADD CONSTRAINT support_messages_ticket_id_fkey FOREIGN KEY (ticket_id) REFERENCES public.support_tickets(id);


--
-- Name: support_tickets support_tickets_assigned_to_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.support_tickets
    ADD CONSTRAINT support_tickets_assigned_to_fkey FOREIGN KEY (assigned_to) REFERENCES public.users(id);


--
-- Name: support_tickets support_tickets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.support_tickets
    ADD CONSTRAINT support_tickets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: transaction_engine_events transaction_engine_events_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.transaction_engine_events
    ADD CONSTRAINT transaction_engine_events_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.unified_transactions(id);


--
-- Name: transaction_engine_events transaction_engine_events_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.transaction_engine_events
    ADD CONSTRAINT transaction_engine_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: transactions transactions_cashout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_cashout_id_fkey FOREIGN KEY (cashout_id) REFERENCES public.cashouts(id);


--
-- Name: transactions transactions_escrow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_escrow_id_fkey FOREIGN KEY (escrow_id) REFERENCES public.escrows(id);


--
-- Name: transactions transactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: unified_transaction_retry_logs unified_transaction_retry_logs_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.unified_transaction_retry_logs
    ADD CONSTRAINT unified_transaction_retry_logs_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.unified_transactions(id);


--
-- Name: unified_transaction_status_history unified_transaction_status_history_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.unified_transaction_status_history
    ADD CONSTRAINT unified_transaction_status_history_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES public.users(id);


--
-- Name: unified_transaction_status_history unified_transaction_status_history_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.unified_transaction_status_history
    ADD CONSTRAINT unified_transaction_status_history_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.unified_transactions(id);


--
-- Name: unified_transactions unified_transactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.unified_transactions
    ADD CONSTRAINT unified_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_achievements user_achievements_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_contacts user_contacts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_contacts
    ADD CONSTRAINT user_contacts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_sessions user_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_sms_usage user_sms_usage_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_sms_usage
    ADD CONSTRAINT user_sms_usage_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_streak_tracking user_streak_tracking_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.user_streak_tracking
    ADD CONSTRAINT user_streak_tracking_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: wallet_balance_snapshots wallet_balance_snapshots_internal_wallet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallet_balance_snapshots
    ADD CONSTRAINT wallet_balance_snapshots_internal_wallet_id_fkey FOREIGN KEY (internal_wallet_id) REFERENCES public.internal_wallets(wallet_id);


--
-- Name: wallet_balance_snapshots wallet_balance_snapshots_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallet_balance_snapshots
    ADD CONSTRAINT wallet_balance_snapshots_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: wallet_holds wallet_holds_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallet_holds
    ADD CONSTRAINT wallet_holds_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: wallets wallets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: cloud_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO neon_superuser WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: cloud_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLES TO neon_superuser WITH GRANT OPTION;


--
-- PostgreSQL database dump complete
--

