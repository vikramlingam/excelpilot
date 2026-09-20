.PHONY: dev serve mcp doctor test lint addin-install addin-build sideload-mac

dev:
	uv run python -m excelpilot serve

serve:
	uv run python -m excelpilot serve

mcp:
	uv run python -m excelpilot mcp

doctor:
	uv run python -m excelpilot doctor

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check .
	uv run mypy server/excelpilot

addin-install:
	cd addin && npm install

addin-build:
	cd addin && npm run build

sideload-mac:
	./scripts/sideload-mac.sh
