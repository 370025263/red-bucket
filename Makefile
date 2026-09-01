# lint 门禁对齐 SkillNerds/xskill Makefile：
# semgrep 官方包 + .semgrep/xskill.yml，ruff / pylint 命名正则走命令行，
# 不把规则选择写进 pyproject.toml。另外按本仓库要求加上 PEP8（E,W）
# 与行宽 79。
# 本地默认 uv + Python 3.12；CI 可覆盖 PY=python3
PY ?= uv run --python 3.12 python
PYTEST := $(PY) -m pytest

.PHONY: test lint lint-custom help

help:
	@echo " make lint        — 交付前门禁（semgrep 官方+自定义 + ruff PEP8 + pylint 命名 + vulture）"
	@echo " make lint-custom — 只跑仓库内 .semgrep/xskill.yml（无网时用）"
	@echo " make test        — 单元测试"

# 范围限 src/ + tests/：openspec/sdd 是规划文档，不进门禁。
# ruff 在 xskill 的 F401,F841,ARG,E722,S110,S112 之上增加 E,W（pycodestyle / PEP8）。
lint:
	semgrep scan --config p/default --config p/python --config p/ai-best-practices \
		--config .semgrep/xskill.yml --error --quiet src tests
	$(PY) -m ruff check src tests --line-length 79 \
		--select E,W,F401,F841,ARG,E722,S110,S112 \
		--per-file-ignores "tests/*:ARG"
	$(PY) -m pylint src/redbucket --disable=all --enable=invalid-name \
		--variable-rgx='[a-z_][a-z0-9_]{2,}$$' --argument-rgx='[a-z_][a-z0-9_]{2,}$$' \
		--attr-rgx='[a-z_][a-z0-9_]{2,}$$' --good-names=i,j,k,v,_ \
		--score=n
	$(PY) -m vulture src/ --min-confidence 80

lint-custom:
	semgrep scan --config .semgrep/xskill.yml --error --quiet src tests
	$(PY) -m ruff check src tests --line-length 79 \
		--select E,W,F401,F841,ARG,E722,S110,S112 \
		--per-file-ignores "tests/*:ARG"
	$(PY) -m pylint src/redbucket --disable=all --enable=invalid-name \
		--variable-rgx='[a-z_][a-z0-9_]{2,}$$' --argument-rgx='[a-z_][a-z0-9_]{2,}$$' \
		--attr-rgx='[a-z_][a-z0-9_]{2,}$$' --good-names=i,j,k,v,_ \
		--score=n
	$(PY) -m vulture src/ --min-confidence 80

test:
	$(PYTEST) tests/ -q
