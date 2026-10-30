# Team contribution workflow

## Start a task

1. Accept the repository invitation and clone the repository using your own GitHub account.
2. Create a task issue using the Task template. Record the owner, estimated effort, deliverable, deadline, and reviewer.
3. Update your local main branch before beginning work:

   ```bash
   git switch main
   git pull --ff-only origin main
   git switch -c member-name/short-task-name
   ```

4. Work in your assigned notebook folder. Put reusable functions in `src/`; coordinate before changing shared code.

## Submit work for review

1. Run the changed notebook from a clean kernel or run the relevant script. Include relative data paths and the source/cleaning version. Report the random seed and actual dependency versions when models are implemented.
2. Save small metric tables to `results/` and figures to `reports/figures/`. Label sample or synthetic results explicitly.
3. Stage only the files you intend to share, commit them, and push your branch:

   ```bash
   git add path/to/your/files
   git commit -m "Describe the completed contribution"
   git push -u origin member-name/short-task-name
   ```

4. On GitHub, open a pull request into `main`, complete the pull-request template, and request a teammate's review.
5. Resolve review feedback and merge through GitHub after review. This is the team's agreed workflow; automated branch protections are not configured by this setup.

## Fair contribution evidence

Use completed tasks, reproducible analysis, interpretations, code review, and integration work as evidence. Keep task issues and pull requests linked. Data preparation and debugging count as technical work; compare estimated effort and delivered outcomes across members.

When documenting an experiment, include the target definition, sample size/exclusions, features, training/validation dates, baseline, model settings, metrics, findings, and limitations. Claims in an individual status report should describe work that person actually performed.

## Data handoff

Member 1 should share an early cleaned sample as soon as the basic field mapping is stable. Agree on the schema and coverage checks before the full data release. Member 2 and Revanth can develop features and weekly aggregation while full cleaning continues. Completion-based labels require reliable documented completion dates and sufficient follow-up for unresolved requests.
