FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY poe_data_mcp ./poe_data_mcp
RUN pip install --no-cache-dir .

ENV MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=47820 \
    POE_DATA_MCP_CACHE_DIR=/cache

EXPOSE 47820
VOLUME /cache
CMD ["poe-data-mcp"]
