FROM golang:1.26.2-alpine3.23 AS builder

ARG PICOCLAW_GIT_REF=v0.2.6

RUN apk add --no-cache git gcc g++ musl-dev olm-dev

WORKDIR /src
RUN git clone https://github.com/sipeed/picoclaw.git .
RUN git checkout "${PICOCLAW_GIT_REF}"
RUN mkdir -p cmd/picoclaw/internal/onboard/workspace
RUN go generate ./... || true
RUN CGO_ENABLED=1 go build -tags whatsapp_native -o /out/picoclaw ./cmd/picoclaw

FROM alpine:3.23

RUN apk add --no-cache ca-certificates tzdata olm wget python3

WORKDIR /root
COPY --from=builder /out/picoclaw /usr/local/bin/picoclaw

RUN mkdir -p /root/.picoclaw

ENTRYPOINT ["picoclaw"]
