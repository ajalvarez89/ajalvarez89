FROM elixir:1.16-otp-26-alpine AS builder

RUN apk add --no-cache build-base git nodejs npm sqlite-dev

WORKDIR /app

ENV MIX_ENV=dev

RUN mix local.hex --force && mix local.rebar --force

COPY mix.exs ./
RUN mix deps.get

COPY config ./config
RUN mix deps.compile

COPY lib ./lib
COPY priv ./priv

RUN mkdir -p /app/data/sqlite

EXPOSE 4000

CMD ["sh", "-c", "mix ecto.create --quiet || true && mix ecto.migrate && mix phx.server"]
