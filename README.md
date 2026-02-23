# zhi

An agentic CLI powered by Zhipu GLM. Create and run custom AI skills from your terminal.

> **Status: Planning Phase** — Architecture and design documents complete. Implementation has not started.

## What is zhi?

`zhi` is an open-source Python CLI that gives you an AI-powered assistant in your terminal. It uses a **two-model architecture**:

- **Interactive chat** uses GLM-5 (smart, agentic) for complex reasoning and skill creation
- **Skill execution** uses GLM-4-flash (cheap, fast) for daily tasks — costing less than 10% of GLM-5

Install with `pip install zhi`, set your Zhipu API key, and start working. First useful output in under 60 seconds.

## Key Features (Planned)

- **Interactive REPL** with streaming responses, thinking mode, and Rich terminal UI
- **Custom skills** — create reusable AI workflows as simple YAML files
- **Built-in tools** — file I/O, OCR, web fetch, shell execution
- **Multimodal input** — drag and drop images, PDFs, and Office documents into the terminal
- **Permission system** — approve mode (confirm risky actions) or auto mode (with shell always requiring confirmation)
- **Cross-platform** — macOS, Windows, and Linux
- **Chinese-first** — CJK text rendering and IME input support

## File Safety

`zhi` will never delete or modify your existing files. All outputs go to a dedicated `./zhi-output/` directory. The shell tool always requires explicit confirmation, even in auto mode.

## Planning Documents

Start with the improved plan, then reference others as needed:

| Document | Description |
|----------|-------------|
| [05-improved-plan.md](./05-improved-plan.md) | **Start here.** Comprehensive implementation plan — architecture, 34 tasks, metrics |
| [01-task-breakdown.md](./01-task-breakdown.md) | Architecture audit with gaps/risks analysis |
| [02-test-strategy.md](./02-test-strategy.md) | Test strategy with ~148 enumerated tests |
| [03-success-metrics.md](./03-success-metrics.md) | Success metrics, KPIs, and performance targets |
| [04-ux-improvements.md](./04-ux-improvements.md) | UX design, competitive analysis, and multimodal input |

## Target Platforms

- macOS (primary development)
- Windows (cross-platform parity via CI)
- Linux (CI-tested)

## Contributing

This project is in the planning phase and is not yet accepting code contributions. If you are interested, read the planning documents above.

## License

MIT
