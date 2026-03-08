# syntax=docker/dockerfile:1.7

# Multi-stage build for netchecks-operator from Rust source.
# Uses cargo-chef to cache dependency compilation as a separate Docker layer.

# ---------------------------------------------------------------------------
# Stage 1: Chef base (shared toolchain for planner + builder)
# ---------------------------------------------------------------------------
FROM rust:1-alpine AS chef

RUN apk add --no-cache musl-dev
RUN cargo install cargo-chef --locked

WORKDIR /build

# ---------------------------------------------------------------------------
# Stage 2: Planner — analyse dependencies and produce a recipe
# ---------------------------------------------------------------------------
FROM chef AS planner

COPY Cargo.toml Cargo.lock ./
COPY src/ src/

RUN cargo chef prepare --recipe-path recipe.json

# ---------------------------------------------------------------------------
# Stage 3: Builder — cook dependencies (cached), then compile source
# ---------------------------------------------------------------------------
FROM chef AS builder

# Cook dependencies — this layer is cached until Cargo.toml/Cargo.lock change
COPY --from=planner /build/recipe.json recipe.json
RUN cargo chef cook --release --recipe-path recipe.json

# Now copy source and build the actual binary (only this recompiles on changes)
COPY Cargo.toml Cargo.lock ./
COPY src/ src/
RUN cargo build --release && \
    install -Dm755 /build/target/release/netchecks-operator /out/netchecks-operator

# ---------------------------------------------------------------------------
# Stage 4: Runtime (distroless)
# ---------------------------------------------------------------------------
FROM cgr.dev/chainguard/static AS runtime

LABEL org.opencontainers.image.source=https://github.com/hardbyte/netchecks
LABEL org.opencontainers.image.description="Netchecks Operator — Kubernetes controller for NetworkAssertion CRDs"

COPY --from=builder /out/netchecks-operator /usr/local/bin/netchecks-operator

USER 65534
ENTRYPOINT ["netchecks-operator"]
