# syntax=docker/dockerfile:1.7

# Multi-stage build for netchecks-operator from Rust source.

# ---------------------------------------------------------------------------
# Stage 1: Build
# ---------------------------------------------------------------------------
FROM rust:1-alpine AS builder

RUN apk add --no-cache musl-dev

WORKDIR /build

# Copy source
COPY Cargo.toml Cargo.lock ./
COPY src/ src/

RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/usr/local/cargo/git \
    --mount=type=cache,target=/build/target \
    cargo build --release && \
    install -Dm755 /build/target/release/netchecks-operator /out/netchecks-operator

# ---------------------------------------------------------------------------
# Stage 2: Runtime (distroless)
# ---------------------------------------------------------------------------
FROM cgr.dev/chainguard/static AS runtime

LABEL org.opencontainers.image.source=https://github.com/hardbyte/netchecks
LABEL org.opencontainers.image.description="Netchecks Operator — Kubernetes controller for NetworkAssertion CRDs"

COPY --from=builder /out/netchecks-operator /usr/local/bin/netchecks-operator

USER 65534
ENTRYPOINT ["netchecks-operator"]
