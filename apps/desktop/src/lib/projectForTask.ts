// Phase 2: map a pressing-item id (e.g. SIDEPROJECT-FOYER-FAMILY-DEPLOY-001)
// to the project slug it belongs to (SIDEPROJECT-FOYER-FAMILY), using prefix
// matching against the live project list from /api/home.projects[].

import type { ProjectListItem } from "../api/client";

/**
 * Return the slug of the longest project that is a strict prefix of the task
 * id, or `null` if no project matches.
 *
 * Match rule: `project.slug === taskId` OR `taskId.startsWith(project.slug + "-")`.
 * The hyphen guard prevents "FOO" from matching "FOOBAR-001".
 * The longest-match preference handles nested tag schemes — e.g. given
 * projects ["FOO", "FOO-BAR"] and task "FOO-BAR-001", "FOO-BAR" wins.
 */
export function projectForTask(
  taskId: string,
  projects: ProjectListItem[],
): string | null {
  let best: string | null = null;
  for (const p of projects) {
    if (taskId === p.slug || taskId.startsWith(p.slug + "-")) {
      if (best === null || p.slug.length > best.length) {
        best = p.slug;
      }
    }
  }
  return best;
}
