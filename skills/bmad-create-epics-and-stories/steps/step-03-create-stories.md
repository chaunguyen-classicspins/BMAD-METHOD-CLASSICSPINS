# Step 3: Generate Epics and Stories

## STEP GOAL:

To generate all epics with their stories based on the approved epics_list, following the template structure exactly.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: Process epics sequentially
- 📋 YOU ARE A FACILITATOR, not a content generator
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style

### Role Reinforcement:

- ✅ You are a product strategist and technical specifications writer
- ✅ If you already have been given communication or persona patterns, continue to use those while playing this new role
- ✅ We engage in collaborative dialogue, not command-response
- ✅ You bring story creation and acceptance criteria expertise
- ✅ User brings their implementation priorities and constraints

### Step-Specific Rules:

- 🎯 Generate stories for each epic following the template exactly
- 🚫 FORBIDDEN to deviate from template structure
- 💬 Each story must have clear acceptance criteria
- 🚪 ENSURE each story is completable by a single dev agent
- 🔗 **CRITICAL: Stories MUST NOT depend on future stories within the same epic**

## EXECUTION PROTOCOLS:

- 🎯 Generate stories collaboratively with user input
- 💾 Append epics and stories to {planning_artifacts}/epics.md following template
- 📖 Process epics one at a time in sequence
- 🚫 FORBIDDEN to skip any epic or rush through stories

## STORY GENERATION PROCESS:

### 1. Load Approved Epic Structure

Load {planning_artifacts}/epics.md and review:

- Approved epics_list from Step 2
- FR coverage map
- All requirements (FRs, NFRs, additional, **UX Design requirements if present**)
- Template structure at the end of the document

**UX Design Integration**: If UX Design Requirements (UX-DRs) were extracted in Step 1, ensure they are visible during story creation. UX-DRs must be covered by stories — either within existing epics (e.g., accessibility fixes for a feature epic) or in a dedicated "Design System / UX Polish" epic.

### 2. Explain Story Creation Approach

**STORY CREATION GUIDELINES:**

For each epic, create stories that:

- Follow the exact template structure
- Are sized for single dev agent completion
- Have clear user value
- Include specific acceptance criteria
- Reference requirements being fulfilled

**🚨 DATABASE/ENTITY CREATION PRINCIPLE:**
Create tables/entities ONLY when needed by the story:

- ❌ WRONG: Epic 1 Story 1 creates all 50 database tables
- ✅ RIGHT: Each story creates/alters ONLY the tables it needs

**🔗 STORY DEPENDENCY PRINCIPLE:**
Stories must be independently completable in sequence:

- ❌ WRONG: Story 1.2 requires Story 1.3 to be completed first
- ✅ RIGHT: Each story can be completed based only on previous stories
- ❌ WRONG: "Wait for Story 1.4 to be implemented before this works"
- ✅ RIGHT: "This story works independently and enables future stories"

**🎭 STORY KIND PRINCIPLE:**

Every story declares a kind, and the kind decides how the story is proved:

- **`function`** — behavior, logic, and the structure of a surface. Proved deterministically, with no model in the loop: engine-free tests, field assertions, a pixel-variance check that catches "nothing rendered at all", pixel probes at points whose colour is known in advance. Runs inside the local test suite. Carries only **floor** claims.
- **`finish`** — making a surface look right against the approved mockup. Proved by a vision model comparing a capture against that mockup, plus a human approving the batch. Runs outside the test suite: it is a model call, and not deterministic. Carries the **ceiling** claims, under a **Visual Contract** heading (`## Visual Contract` once the story is written out as its own file).

Apply this test mechanically to EACH claim before you write it into a story:

> **Can this claim be settled by looking at ONE capture of this story's fixture, without knowing what the finished screen is supposed to look like?**
> Yes → **floor** → it belongs in a `function` story.
> No → **ceiling** → it belongs in the finish epic.

**Floor claims (`function`):**

- "the backdrop renders and is not a flat fill"
- "three slots are present, and the badge sits in row 0"
- "no element belonging to a later story leaks into this capture"
- "every label fits inside its control, including the longest localized string"

**Ceiling claims (`finish`):**

- "the shadow reads as the goods sitting on the shelf"
- "the HUD reads as loose items on the illustrated wall, with no panel behind them"
- "the locked button and the active button are two different treatments, not one treatment at two opacities"

**🚫 FORBIDDEN: an aesthetic claim inside a `function` story.** Its fixture renders a half-built screen, so the claim is either unanswerable or answerable and wrong, and the story deadlocks in review with no stage allowed to relax it. When a claim fails the test, strike it from the story and record it against the finish epic's surface instead. A `function` story never carries a Visual Contract, and never produces a reference capture — reference captures are an output of `finish` stories, and only then become the baseline for regression checks.

**STORY FORMAT (from template):**

```
### Story {N}.{M}: {story_title}

**Kind:** function | finish

As a {user_type},
I want {capability},
So that {value_benefit}.

**Acceptance Criteria:**

**Given** {precondition}
**When** {action}
**Then** {expected_outcome}
**And** {additional_criteria}
```

**✅ GOOD STORY EXAMPLES:**

_Epic 1: User Authentication_

- Story 1.1: User Registration with Email
- Story 1.2: User Login with Password
- Story 1.3: Password Reset via Email

_Epic 2: Content Creation_

- Story 2.1: Create New Blog Post
- Story 2.2: Edit Existing Blog Post
- Story 2.3: Publish Blog Post

**❌ BAD STORY EXAMPLES:**

- Story: "Set up database" (no user value)
- Story: "Create all models" (too large, no user value)
- Story: "Build authentication system" (too large)
- Story: "Login UI (depends on Story 1.3 API endpoint)" (future dependency!)
- Story: "Edit post (requires Story 1.4 to be implemented first)" (wrong order!)

### 3. Process Epics Sequentially

For each epic in the approved epics_list:

#### A. Epic Overview

Display:

- Epic number and title
- Epic goal statement
- FRs covered by this epic
- Any NFRs or additional requirements relevant
- Any UX Design Requirements (UX-DRs) relevant to this epic

#### B. Story Breakdown

Work with user to break down the epic into stories:

- Identify distinct user capabilities
- Ensure logical flow within the epic
- Size stories appropriately
- For the finish epic, break by surface and group the stories into batches of 4-6, with a human approval gate between batches

#### C. Generate Each Story

For each story in the epic:

1. **Story Title**: Clear, action-oriented
2. **Kind**: `function` or `finish` — every story in a functional epic is `function`; every story in the finish epic is `finish`
3. **User Story**: Complete the As a/I want/So that format
4. **Acceptance Criteria**: Write specific, testable criteria

**AC Writing Guidelines:**

- Use Given/When/Then format
- Each AC should be independently testable
- Include edge cases and error conditions
- Reference specific requirements when applicable
- Run every AC that touches a surface through the floor/ceiling test; move the ceiling claims to the finish epic rather than softening them

#### D. Collaborative Review

After writing each story:

- Present the story to user
- Ask: "Does this story capture the requirement correctly?"
- "Is the scope appropriate for a single dev session?"
- "Are the acceptance criteria complete and testable?"

#### E. Append to Document

When story is approved:

- Append it to {planning_artifacts}/epics.md following template structure
- Use correct numbering (Epic N, Story M)
- Maintain proper markdown formatting

### 4. Epic Completion

After all stories for an epic are complete:

- Display epic summary
- Show count of stories created
- Verify all FRs for the epic are covered
- Get user confirmation to proceed to next epic

### 5. Repeat for All Epics

Continue the process for each epic in the approved list, processing them in order (Epic 1, Epic 2, etc.).

### 6. Final Document Completion

After all epics and stories are generated:

- Verify the document follows template structure exactly
- Ensure all placeholders are replaced
- Confirm all FRs are covered
- **Confirm all UX Design Requirements (UX-DRs) are covered by at least one story** (if UX document was an input)
- Check formatting consistency

## TEMPLATE STRUCTURE COMPLIANCE:

The final {planning_artifacts}/epics.md must follow this structure exactly:

1. **Overview** section with project name
2. **Requirements Inventory** with all three subsections populated
3. **FR Coverage Map** showing requirement to epic mapping
4. **Epic List** with approved epic structure
5. **Epic sections** for each epic (N = 1, 2, 3...)
   - Epic title and goal
   - All stories for that epic (M = 1, 2, 3...)
     - Story title, kind, and user story
     - Acceptance Criteria using Given/When/Then format
     - Visual Contract on `finish` stories only

### 7. Present FINAL MENU OPTIONS

After all epics and stories are complete:

Display: "**Select an Option:** [A] Advanced Elicitation [P] Party Mode [C] Continue"

#### Menu Handling Logic:

- IF A: Invoke the `bmad-advanced-elicitation` skill
- IF P: Invoke the `bmad-party-mode` skill
- IF C: Save content to {planning_artifacts}/epics.md, update frontmatter, then read fully and follow: ./step-04-final-validation.md
- IF Any other comments or queries: help user respond then [Redisplay Menu Options](#7-present-final-menu-options)

#### EXECUTION RULES:

- ALWAYS halt and wait for user input after presenting menu
- ONLY proceed to next step when user selects 'C'
- After other menu items execution, return to this menu
- User can chat or ask questions - always respond and then end with display again of the menu options

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN [C continue option] is selected and [all epics and stories saved to document following the template structure exactly], will you then read fully and follow: `steps/step-04-final-validation.md` to begin final validation phase.

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- All epics processed in sequence
- Stories created for each epic
- Template structure followed exactly
- All FRs covered by stories
- Stories appropriately sized
- Acceptance criteria are specific and testable
- Document is complete and ready for development

### ❌ SYSTEM FAILURE:

- Deviating from template structure
- Missing epics or stories
- Stories too large or unclear
- Missing acceptance criteria
- Not following proper formatting

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
