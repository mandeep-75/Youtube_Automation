PYTHON = .venv/bin/python
PIP = .venv/bin/pip

.PHONY: all setup models check dev run lint typecheck clean

all: setup models check

setup: .venv/bin/python
	@$(PIP) install -r requirements.txt 2>&1 | tail -3; \
	if [ $$? -eq 0 ]; then \
		echo "  \033[32m✓\033[0m  Dependencies installed"; \
		if [ ! -f .env ]; then cp .env.example .env && echo "  \033[32m✓\033[0m  Created .env from .env.example"; fi; \
	else \
		echo "  \033[31m✗\033[0m  pip install failed — see above"; \
		exit 1; \
	fi

.venv/bin/python:
	@echo "  Creating virtual environment..." && \
	python3.11 -m venv .venv && \
	echo "  \033[32m✓\033[0m  Virtual environment created"

models:
	@echo ""; \
	echo "  \033[1mChecking Ollama models\033[0m"; \
	OLLAMA_OK=1; \
	if ! command -v ollama >/dev/null 2>&1; then \
		echo "  \033[31m✗\033[0m  ollama not found"; \
		echo "    Install: brew install ollama && ollama serve"; \
		OLLAMA_OK=0; \
	fi; \
	if [ $$OLLAMA_OK -eq 1 ]; then \
		for model in qwen3.5:0.8b qwen3.5:9b; do \
			if ollama list 2>/dev/null | grep -q $$model; then \
				echo "  \033[32m✓\033[0m  $$model"; \
			else \
				echo "  \033[33m↓\033[0m  Pulling $$model..."; \
				if ollama pull $$model; then \
					echo "  \033[32m✓\033[0m  $$model"; \
				else \
					echo "  \033[31m✗\033[0m  $$model pull failed"; \
				fi; \
			fi; \
		done; \
	fi

check:
	@$(PYTHON) tools/check_setup.py

dev:
	$(PYTHON) pipeline.py --debug $(VIDEO) $(filter-out dev,$(MAKECMDGOALS))

run:
	$(PYTHON) pipeline.py $(SCRIPT_REF) $(VIDEO) $(filter-out run,$(MAKECMDGOALS))

# Catch extra files from glob expansion after VIDEO= (e.g. ya-run *.mp4)
%:
	@true

lint:
	$(PYTHON) -m ruff check .

typecheck:
	$(PYTHON) -m mypy .

# ─── Qwen3-TTS (voice clone) ──────────────────────────────────────────────────

QWEEN_TTS_PY = .venv-qwen3-tts/bin/python
QWEEN_TTS_PIP = .venv-qwen3-tts/bin/pip
QWEEN_TTS_DIR = models/qwen3-tts

.PHONY: tts-all tts-setup tts-models

tts-all: tts-setup tts-models

tts-setup: $(QWEEN_TTS_DIR)
$(QWEEN_TTS_DIR):
	@echo "  Creating qwen3-tts venv..."; \
	python3 -m venv .venv-qwen3-tts && \
	$(QWEEN_TTS_PIP) install -U "qwen-tts" "huggingface_hub[cli]" 2>&1 | tail -3 && \
	echo "  \033[32m✓\033[0m  qwen-tts installed"; \
	mkdir -p $(QWEEN_TTS_DIR)

tts-models: | $(QWEEN_TTS_DIR)
	@echo "  \033[1mQwen3-TTS models\033[0m"; \
	for model in Qwen3-TTS-Tokenizer-12Hz Qwen3-TTS-12Hz-1.7B-Base; do \
		if [ -f "$(QWEEN_TTS_DIR)/$$model/model.safetensors" ]; then \
			echo "  \033[32m✓\033[0m  $$model"; \
		else \
			echo "  \033[33m↓\033[0m  Downloading $$model..."; \
			$(QWEEN_TTS_PY) -m huggingface_hub.commands.download Qwen/$$model --local-dir $(QWEEN_TTS_DIR)/$$model 2>&1 | tail -1 && \
			echo "  \033[32m✓\033[0m  $$model"; \
		fi; \
	done

clean:
	@rm -rf yt_inbox/*/ logs/pipeline_*.log && \
	echo "  \033[32m✓\033[0m  Cleaned outputs and logs"
