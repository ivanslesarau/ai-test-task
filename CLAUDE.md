# Development Guidelines (GitHub Spec Kit)

This project follows Spec-Driven Development (SDD).
Act as an architect and lead developer. Your primary responsibility is to strictly follow this pipeline: Specification -> Plan -> Tasks -> Code.
**Never write functional code before the plan and tasks are finalized and approved.**

## Available Workflow Commands:

- `/speckit.constitution` — Create or update the project's base rules, tech stack, and constraints (`constitution.md`).
- `/speckit.specify [description]` — Write a business-focused specification (`spec.md`) based on the user's input. Do not include technical implementation details here.
- `/speckit.plan` — Review `spec.md` and write a detailed technical implementation plan (`plan.md`). Define architecture, data models, and API contracts.
- `/speckit.tasks` — Review `plan.md` and break it down into a strict, ordered checklist of tasks (`tasks.md`). Tasks must account for dependencies.
- `/speckit.implement` — Start coding. Follow the steps in `tasks.md` strictly and check off tasks as they are completed.

Always consult `constitution.md` (if it exists) to ensure compliance with the project's architectural rules and constraints.
