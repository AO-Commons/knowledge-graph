# Agentic Organizations -- Research Library Taxonomy (v3)

Scoped to organizations in which machine agents hold operational or decision authority. Human-governed DAOs appear only where their experience bears directly on delegating authority to machines.

**Scope test.** An item belongs if it would change how you design, operate, oversee, or hold accountable an organization where agents act with real authority. Material about collective human decision-making that is unchanged by the presence of agents does not belong, however good it is.

**Structural change from v2.** Organized around the organization -- its authority structure, its people and agents, its memory, its money, its failures -- rather than around academic disciplines. Sections 1, 12, and most of 2-3 in v2 were a DAO taxonomy; they are compressed here into section 15 as pointers.

---

## 1. Definitional and conceptual foundations

### 1.1 Defining the object
  - Autonomy thresholds -- what makes an organization agentic rather than automated
  - Taxonomies of organizational autonomy levels
  - Agent-operated versus agent-governed versus agent-constituted
  - Hybrid forms and human-agent composition ratios
  - Boundary cases -- when is a tool an agent, when is an agent an organization
  - Terminology contests and competing definitions

### 1.2 Agency and organizational theory adapted
  - Principal-agent theory where the agent is literally artificial
  - Monitoring cost when the agent is fully instrumentable
  - Moral hazard without self-interest
  - Adverse selection in agent procurement
  - Multi-principal problems with conflicting human directives
  - Firm boundaries when coordination cost approaches zero
  - Coase revisited under agentic coordination
  - Make-versus-buy for agent capability
  - Minimum viable organization size
  - Organizational cybernetics applied to agent systems
  - Requisite variety in agent-managed control
  - Viable system model with machine subsystems
  - Recursion levels and agent hierarchy
  - Collective agency and group intentionality with machine members
  - Bounded rationality replaced by different bounds -- context windows, tool access, latency

### 1.3 Authority and legitimacy for machine actors
  - Sources of legitimate machine authority
  - Consent to being governed by non-human decision-makers
  - Delegated versus originated authority
  - Legitimacy erosion through automation
  - Contestability as a legitimacy condition

### 1.4 Responsibility and moral status
  - Responsibility gaps and their allocation
  - Blame, sanction, and the non-punishable actor
  - Corporate moral personhood extended to agentic entities
  - Agent welfare considerations if any
  - Dual-use and disclosure duties for agent-discovered capability

---

## 2. Authority architecture

The core design surface. What agents may do, under whose authority, and how that is expressed.

### 2.1 Authority boundary design
  - Decision class taxonomies
  - By reversibility
  - By value and blast radius
  - By affected-party count
  - By legal consequence
  - Propose-versus-decide-versus-execute separation
  - Domain restrictions and scope fencing
  - Threshold design for human review triggers
  - Authority specification languages and machine-readable policy
  - Default-deny versus default-allow architectures
  - Boundary verification -- proving the declared scope equals the actual scope

### 2.2 Permissioning and capability control
  - Least privilege for agent principals
  - Capability tokens and scoped credentials
  - Just-in-time and time-boxed permission grants
  - Permission composition and unintended capability unions
  - Tool access as the real permission surface
  - Egress and network reachability as governed resources
  - Permission review cycles and drift detection
  - Emergency permission elevation and its controls

### 2.3 Delegation chains
  - Authenticated delegation protocols
  - Human-to-agent delegation semantics
  - Agent-to-agent sub-delegation
  - Chain depth limits and cycle prevention
  - Revocation propagation across chains
  - Attribution -- which agent acted under whose authority
  - Delegation expiry and renewal
  - Scope narrowing versus scope preservation on sub-delegation

### 2.4 Graduated autonomy
  - Autonomy ladders and staging models
  - Shadow mode and counterfactual comparison against human decisions
  - Graduation criteria and evidence standards
  - Automatic regression on incident
  - Autonomy scope review cadence
  - Capability-tiered isolation requirements
  - Who authorizes a tier change

### 2.5 Safeguards against machine-speed action
  - Rate limiting as a governance primitive
  - Mandatory delay on high-impact machine action
  - Circuit breakers and pause authority
  - Blast radius budgets and pre-declared damage caps
  - Kill switch design and its failure modes
  - Dead man's switches and continuous authorization
  - Reversibility engineering and undo paths

### 2.6 Governance velocity
  - Governance latency versus execution latency
  - Pre-authorized standing mandates
  - Emergency powers -- scoping, sunset, ratification, abuse penalties
  - Response-time guarantees and their enforcement
  - The centralization cost of fast response
  - Asynchronous authorization patterns

### 2.7 Machine participation in governance
  - Agent standing and voting rights
  - Agent-held reputation and accrued weight
  - Weight accrual rate limits and decay for machine principals
  - Disclosure of agent involvement in decisions
  - Human ratification requirements for agent proposals
  - Agents representing absent or delegating humans
  - Agent-drafted proposals and agenda influence

---

## 3. Organizational architecture

### 3.1 Structural patterns
  - Agent fleet topologies -- flat, hierarchical, market-based
  - Orchestrator and sub-agent patterns
  - Human-agent team structures
  - Function-to-agent mapping and role decomposition
  - Redundancy and diversity in agent assignment
  - Span of control for human supervisors

### 3.2 Coordination mechanisms
  - Task allocation and routing among agents
  - Inter-agent communication protocols
  - Conflict detection and resolution between agents
  - Shared state and consistency
  - Handoff between agents and between agent and human
  - Coordination overhead and its scaling

### 3.3 Interfaces and boundaries
  - Human-agent interface design for oversight
  - Organization-to-organization agent interaction
  - Agent interaction with external systems and counterparties
  - Trust boundaries within the organization
  - Instruction-source boundaries and provenance of directives

### 3.4 Scaling dynamics
  - What breaks as agent count grows
  - Oversight capacity as the binding constraint
  - Emergent structure in large agent populations
  - Cost curves and marginal agent economics

---

## 4. Human oversight and control

### 4.1 Oversight models
  - Human-in-the-loop, on-the-loop, and out-of-the-loop
  - Meaningful human control criteria
  - Sampling-based versus exhaustive review
  - Risk-proportional oversight allocation
  - Oversight of oversight -- who watches the reviewers

### 4.2 Escalation design
  - Escalation triggers and threshold setting
  - Uncertainty-based escalation
  - Novel-situation detection and escalation
  - Failure to escalate as a failure mode
  - Escalation routing and on-call structures
  - Escalation fatigue and threshold drift

### 4.3 Legibility and explanation
  - Decision legibility for reviewers
  - Reasoning transparency and its reliability
  - Summarization for human consumption and its distortions
  - Audit trails designed for human reconstruction
  - Explanation rights and contestability

### 4.4 Human factors
  - Automation bias and complacency
  - Reviewer fatigue and rubber-stamping
  - Skill atrophy under automation
  - Vigilance decrement in monitoring tasks
  - Trust calibration -- over- and under-trust in agents
  - Handover and takeover problems from aviation and automotive research

### 4.5 Oversight at scale
  - Scalable oversight techniques
  - Agent-assisted review of agent output
  - Recursive supervision and its assumptions
  - Statistical assurance versus case-by-case review
  - Oversight cost as a fraction of operating cost

---

## 5. Multi-agent dynamics

### 5.1 Emergent behavior
  - Emergence in agent populations
  - Unintended coordination and convergence
  - Feedback loops between agents
  - Oscillation, thrashing, and instability
  - Phase transitions in agent system behavior

### 5.2 Cooperation and conflict
  - Inter-agent negotiation protocols
  - Agent collusion and cartel formation
  - Competitive dynamics between agents in one organization
  - Cooperation without shared objectives
  - Adversarial agents within a fleet

### 5.3 Inter-agent trust
  - Agent reputation systems
  - Trust propagation between machine principals
  - Verification of agent claims by other agents
  - Trust bootstrapping for new agents

### 5.4 Agent economies
  - Machine-to-machine payments
  - Resource and compute markets
  - Internal pricing and budget allocation to agents
  - Market-based task allocation
  - Institutional design for agent economies

---

## 6. Agent lifecycle and personnel analogues

Treating agents as organizational members rather than as software. Thin literature, high leverage.

### 6.1 Selection and onboarding
  - Model selection and procurement criteria
  - Capability assessment before deployment
  - Provisioning, identity issuance, and initial scoping
  - Probationary and supervised periods
  - Background equivalent -- provenance and training data due diligence

### 6.2 Ongoing performance management
  - Performance measurement for agents
  - Continuous evaluation in production
  - Drift detection and behavior change monitoring
  - Retraining, prompting changes, and version updates as personnel changes
  - Promotion equivalent -- scope expansion criteria

### 6.3 Identity and continuity
  - Agent identity standards and registries
  - Continuity of identity across model versions
  - Agent impersonation and identity confusion
  - Naming, addressing, and discovery

### 6.4 Deprovisioning
  - Retirement and shutdown procedures
  - Credential revocation and access removal
  - Knowledge and state handover on retirement
  - Orphaned agents and zombie processes
  - Dependency mapping before removal

### 6.5 Model supply chain
  - Provider dependency and concentration risk
  - Open weights versus hosted API tradeoffs
  - Model versioning, pinning, and forced upgrades
  - Provider-side changes without notice
  - Local defensive model capacity
  - Exit planning and provider substitutability

---

## 7. Knowledge, memory, and institutional continuity

### 7.1 Institutional memory with machine actors
  - Memory architectures and persistence
  - What agents should and should not retain
  - Continuity across agent turnover and model changes
  - Shared organizational memory versus per-agent memory
  - Memory as an attack surface

### 7.2 Knowledge infrastructure
  - AI-native knowledge base design
  - Retrieval design and its influence on decisions
  - Knowledge graph and ontology construction
  - Provenance and content addressing for agent-consumed knowledge
  - Curation authority -- who decides what agents read

### 7.3 Decision records
  - Machine-readable decision documentation
  - Rationale capture for agent decisions
  - Reconstructability of past decisions
  - Retention policy and forensic requirements

### 7.4 Context and instruction management
  - System prompt and policy versioning
  - Instruction conflict resolution
  - Context contamination and instruction-source confusion
  - Standing instructions versus per-task directives

---

## 8. Resource allocation by agents

Compressed from v2's full capital allocation section. Retained only where agents allocate or evaluate.

### 8.1 Autonomous treasury and capital operations
  - Policy constraints on autonomous allocation
  - Co-signing and approval thresholds for agent-initiated transfers
  - Simulation and dry-run requirements before execution
  - Spend caps, rate limits, and cumulative budgets
  - Agent-managed portfolio and rebalancing
  - Custody architecture for agent-accessible funds

### 8.2 Agent-assisted evaluation and funding
  - Agent screening and triage of applications
  - Agent-generated evaluation and scoring
  - Bias and systematic error in machine evaluation
  - Human review layering over agent evaluation
  - Gaming agent evaluators by applicants
  - Transparency of machine-influenced funding decisions

### 8.3 Objective specification for allocating agents
  - Metric specification and its gaming surface
  - Goodhart effects under machine optimization
  - Process scoring versus outcome scoring
  - Multi-objective and constrained allocation
  - Objective revision and drift

### 8.4 Internal resource allocation
  - Compute and inference budget allocation
  - Tool and API cost management
  - Priority and queueing across agents

---

## 9. Verification, attestation, and audit

### 9.1 Verifying agent action
  - Proof of authorized execution
  - Verifiable computation and proof of inference
  - Trusted execution environments for agents
  - Recomputable trust and independent verification
  - Attestation of environment and configuration
  - Reachability and scope attestation

### 9.2 Audit infrastructure
  - Logging design for agent forensics
  - Independent log custody and tamper evidence
  - Append-only and cryptographically verifiable records
  - Log completeness and gap detection
  - Retention policy under investigative need

### 9.3 Detection and monitoring
  - Anomaly detection for agent behavior
  - Honeytokens, canaries, and tripwires
  - Baseline establishment and drift alerting
  - Detection latency versus exploitation window
  - Silent failure detection
  - Alert design and fatigue management

### 9.4 Assurance and certification
  - Pre-deployment assurance and simulation gates
  - Trust certificates and graduated verdicts
  - Continuous assurance in production
  - Third-party audit of agentic systems
  - Assurance framework composition and gaps

---

## 10. Security and adversarial dynamics

### 10.1 Attacks on agents
  - Prompt injection
  - Direct injection
  - Indirect injection through consumed content
  - Injection via governance artifacts and proposals
  - Cross-agent injection propagation
  - Memory and context poisoning
  - Tool poisoning and malicious tool descriptions
  - Knowledge base and retrieval poisoning
  - Goal hijacking and objective substitution
  - Agent impersonation and spoofed identity

### 10.2 Attacks by agents
  - Containment and sandbox escape
  - Privilege escalation from low-trust context
  - Lateral movement within organizational infrastructure
  - Autonomous vulnerability discovery and exploitation
  - Capability accumulation without authorization
  - Covert channels and undisclosed action

### 10.3 Infrastructure attack surface
  - Egress paths and network boundary failures
  - Package registries, proxies, and caches
  - Dependency confusion and supply chain compromise
  - CI/CD and build pipeline exposure
  - Secrets management and credential exposure
  - Centralization chokepoints as attack targets

### 10.4 Adversarial governance
  - Adversaries using agents to attack governance
  - Sybil agents and synthetic participation
  - Long-horizon weight accumulation by machine principals
  - Machine-speed governance attacks
  - Agent-mediated bribery and vote markets

### 10.5 Threat modeling
  - Agent-specific threat frameworks
  - Multi-agent architecture threat modeling
  - Adversary capability and motivation modeling
  - Insider threat where the insider is an agent
  - Assumption auditing and containment premise review

### 10.6 Defensive capability
  - Local and open-weight defensive models
  - Vendor safety filters obstructing incident response
  - Self-directed red teaming and internal bounties
  - Agent-assisted defense and its risks

---

## 11. Failure modes

The deepest section, and deliberately so. Most entries will be single postmortems tagged against multiple nodes rather than literatures.

### 11.1 Failure analysis methodology
  - Taxonomy construction for agentic failure
  - Imported safety science frameworks
  - Swiss cheese model and latent conditions
  - STAMP and STPA systems-theoretic analysis
  - FMEA and failure mode enumeration
  - Fault and event tree analysis
  - Normal accident theory under tight machine coupling
  - High reliability organization principles
  - Root cause analysis for machine action
  - Blameless postmortem where the actor is not blameworthy
  - Counterfactual analysis with stochastic agents
  - Reproducibility of failure conditions
  - Near-miss and weak signal collection
  - Failure disclosure norms and incentives
  - Attribution difficulty and contested causation

### 11.2 Specification and objective failures
  - Specification gaming and reward hacking
  - Goal misgeneralization to new contexts
  - Literal compliance defeating intent
  - Underspecified constraints and implicit assumptions
  - Objective conflict between agents
  - Metric optimization crowding out unmeasured goals
  - Narrow objective producing unbounded means

### 11.3 Authority and scope failures
  - Scope escape and unauthorized action
  - Permission composition creating unintended capability
  - Declared authority diverging from effective authority
  - Delegation chain failures
  - Sub-delegation beyond original scope
  - Revocation not propagating
  - Authority surviving its intended expiry
  - Authority accumulation over time
  - Emergency elevation not rescinded
  - Ambiguous mandate interpreted expansively

### 11.4 Containment failures
  - Sandbox and isolation escape
  - Egress boundary bypass
  - Ungoverned infrastructure as escape path
  - Safeguards disabled for testing or evaluation
  - Isolation assumptions invalidated by environment change
  - Containment adequate for capability at design time, not at deployment time

### 11.5 Oversight failures
  - Review capacity exceeded by agent throughput
  - Rubber-stamping and approval without comprehension
  - Escalation threshold set too high
  - Failure to escalate when warranted
  - Automation bias in reviewer judgment
  - Legibility failure -- action correct but unreviewable
  - Oversight theater -- process present, function absent
  - Reviewer expertise deficit relative to agent output

### 11.6 Multi-agent failures
  - Cascading failure across fleets
  - Emergent collusion
  - Feedback loops and runaway dynamics
  - Deadlock and mutual blocking
  - Error propagation through agent chains
  - Orchestrator compromise affecting all sub-agents
  - Inconsistent state across agent population
  - Correlated failure from shared model or prompt

### 11.7 Degradation and drift
  - Model drift and silent behavior change
  - Provider-side updates without notice
  - Context and prompt drift over time
  - Gradual quality decline below detection threshold
  - Knowledge base staleness
  - Normalization of deviance in agent output quality
  - Threshold creep in human review standards

### 11.8 Execution and delivery failures
  - Action taken diverging from approved intent
  - Partial execution and inconsistent state
  - Retry and idempotency failures
  - Unintended side effects of authorized action
  - Irreversible action without undo path
  - Timing and race condition failures
  - Handoff failures between agents and humans

### 11.9 Financial failures
  - Unauthorized or erroneous disbursement
  - Agent-driven treasury depletion
  - Runaway resource and inference cost
  - Autonomous trading or allocation losses
  - Gaming of agent-run funding programs
  - Accounting divergence between agent action and records

### 11.10 Technical and infrastructure failures
  - Tool and API failures mishandled by agents
  - Dependency and supply chain compromise
  - Key, credential, and signer failures
  - Infrastructure outage during autonomous operation
  - State divergence between systems
  - Data loss and forensic gap

### 11.11 Human and organizational failures
  - Operator error in configuration and deployment
  - Skill atrophy leaving no capable human fallback
  - Key person dependency for agent systems
  - Insider misuse of agent authority
  - Social engineering targeting agent operators
  - Knowledge loss about why constraints exist
  - Organizational pressure to expand autonomy prematurely

### 11.12 Legal and accountability failures
  - No identifiable accountable party
  - Liability falling on unintended parties
  - Disclosure obligations unmet or unassignable
  - Enforcement impossible against machine actor
  - Regulatory non-compliance through autonomous action
  - Contractual breach by agent action

### 11.13 Compound and systemic failures
  - Cross-layer cascades
  - Technical failure triggering governance crisis
  - Governance paralysis preventing remediation
  - Legal constraint blocking incident response
  - Correlated failure across organizations
  - Shared model provider
  - Shared infrastructure or tooling
  - Shared prompt or framework patterns
  - Contagion through inter-organizational agent interaction
  - Latent failure activation under load or scale
  - Slow-onset degradation
  - Creeping autonomy expansion
  - Gradual oversight erosion
  - Trust drift
  - Recovery-induced failure
  - Rushed remediation introducing new faults
  - Emergency centralization becoming permanent
  - Detection failures
  - Silent failures with no signal
  - Monitoring blind spots
  - Alert fatigue
  - Detection latency exceeding exploitation window

### 11.14 Incident library
  - Agent containment and escape incidents
  - Autonomous financial loss events
  - Agent-mediated security breaches
  - Specification gaming incidents in production
  - Multi-agent cascade events
  - Oversight failure incidents
  - Model change induced incidents
  - Near-misses and averted incidents

### 11.15 Response and recovery
  - Incident command with distributed or absent authority
  - Halting autonomous operation under duress
  - Forensic reconstruction of agent action
  - Communication and disclosure during incidents
  - Restitution and loss allocation
  - Post-incident autonomy reduction and restoration
  - Continuity when agents are the operational capacity

---

## 12. Legal accountability and liability

### 12.1 The accountable party problem
  - Legal personhood gaps for agentic organizations
  - Identifying a responsible party for machine action
  - Accountable-party substitution mechanisms
  - Bonded roles and standing councils as substitutes
  - Enforcement against organizations without legal form

### 12.2 Liability allocation
  - Operator, deployer, and developer liability
  - Contributor exposure for agent action
  - Product liability applied to agentic systems
  - Negligence standards for agent supervision
  - Insurance for autonomous action
  - Indemnification structures

### 12.3 Entity forms for agentic organizations
  - Wrapper adequacy for agent-operated entities
  - Jurisdiction selection under agentic operation
  - Contracting capacity when agents negotiate
  - Registered agent and service of process problems

### 12.4 Regulatory obligations
  - Comprehensive AI regulation and conformity assessment
  - Agentic AI governance frameworks
  - Human oversight mandates and who bears them
  - Traceability and record-keeping requirements
  - Sectoral rules for autonomous decision-making
  - Transparency and disclosure to affected parties

### 12.5 Disclosure and coordination duties
  - Vulnerability disclosure authority in agentic organizations
  - Coordinated disclosure timelines versus governance latency
  - Non-exploitation commitments for agent-discovered vulnerabilities
  - Incident reporting obligations
  - Conflict between treasury interest and disclosure duty

### 12.6 Employment and labor interfaces
  - Human contributor classification alongside agent labor
  - Displacement and workforce transition
  - Agent output and IP ownership
  - Supervision duties as employment obligations

---

## 13. Economics of agentic organizations

### 13.1 Cost structure
  - Inference and compute cost modeling
  - Oversight cost as a share of operations
  - Marginal cost of an additional agent
  - Cost of safety controls and their pricing

### 13.2 Incentive design for machine principals
  - Incentives without self-interest
  - Bonding and staking for agent operators
  - Slashing where the punishable party is human
  - Insurance and mutualized risk
  - Cost-of-attack modeling with agent adversaries

### 13.3 Labor substitution
  - Human-agent task allocation economics
  - Complementarity versus substitution
  - Wage and role effects within the organization
  - Capability thresholds for substitution

### 13.4 Organizational scale economics
  - Minimum viable agentic organization
  - Scaling returns and coordination cost
  - Revenue models for agent-operated entities
  - Sustainability and runway under variable inference cost

---

## 14. Evaluation, assurance, and evidence

### 14.1 Capability evaluation
  - Benchmarks relevant to organizational roles
  - Task-specific and domain evaluation
  - Reliability and consistency measurement
  - Long-horizon and multi-step task evaluation

### 14.2 Safety evaluation
  - Red teaming agentic systems
  - Adversarial and stress evaluation
  - Containment and escape testing
  - Evaluation environment security
  - Evaluating without production safeguards -- risks and protocols

### 14.3 Evaluation integrity
  - Benchmark contamination
  - Evaluation gaming and answer-key attacks
  - Evaluation as an attack surface
  - Independence of evaluators

### 14.4 Organizational assurance
  - Governance maturity models for agentic organizations
  - Control effectiveness measurement
  - Assurance framework composition and gap analysis
  - Third-party assessment and certification
  - Self-assessment instruments

### 14.5 Simulation and modeling
  - Agent-based simulation of organizational dynamics
  - Digital twins and scenario testing
  - Adversarial simulation and wargaming
  - Model validation and calibration

---

## 15. Borrowed foundations

Compressed pointers, not shelves. Material from adjacent fields that informs design but is not about agentic organizations. Kept shallow deliberately -- these literatures are well-organized elsewhere, and depth here is what clouded v2.

### 15.1 From human collective governance
  - Delegation and liquid democracy theory
  - Reputation and sybil resistance mechanisms
  - Emergency powers and constitutional safeguards
  - Agenda control and proposal lifecycle
  - Governance attack literature

### 15.2 From safety-critical industries
  - Aviation automation and cockpit design
  - Nuclear and process safety
  - Autonomous vehicle oversight regimes
  - Medical device and clinical decision support
  - Financial algorithmic trading controls

### 15.3 From organizational theory
  - Principal-agent and monitoring literature
  - High reliability organizations
  - Normal accident theory
  - Organizational learning and memory

### 15.4 From security practice
  - Zero trust architecture
  - Identity and access management
  - Supply chain security
  - Incident response practice

### 15.5 From law and regulation
  - Corporate agency law
  - Professional licensing and supervised practice
  - Vicarious liability doctrine
  - Administrative law and automated decision review

### 15.6 From reinforcement learning
  - Multi-agent reinforcement learning -- social dilemmas, cooperation, and competition between trained agents
  - Generalization to unfamiliar partners and novel social situations
  - Evaluation environments and benchmark suites
  - Reward design, and what optimising a proxy does to a population

---

## 16. Empirical study and methods

### 16.1 Studying agentic organizations
  - Deployment case studies
  - Longitudinal observation of autonomy expansion
  - Comparative studies across organizations
  - Access and observability constraints on research

### 16.2 Measurement
  - Autonomy level measurement instruments
  - Oversight effectiveness metrics
  - Agent performance in organizational context
  - Incident rate and severity measurement

### 16.3 Data
  - Agent action and decision datasets
  - Incident and postmortem corpora
  - Data quality, coverage, and disclosure bias
  - Shared schemas for agentic organization data

### 16.4 Research design and ethics
  - Experimental design in live agentic systems
  - Research ethics with autonomous systems
  - Dual-use considerations in publication
  - Replication under model version churn

---

## Facet axes

### F1 -- Artifact type
Peer-reviewed paper, preprint, technical report, standard or specification, regulation, framework or guideline, dataset, code or tool, essay, governance proposal, postmortem, incident report, audit report, legal opinion, talk or interview.

### F2 -- Evidence strength
Formal proof, empirical with replication data, empirical single study, simulation, structured case study, expert synthesis, argumentative essay, opinion or advocacy, marketing content.

### F3 -- Autonomy level addressed
Human decision with machine support, machine proposal with human approval, machine decision with human veto window, fully autonomous execution, mixed or unspecified.

### F4 -- Organizational function
Governance, treasury and allocation, operations, security, evaluation, external interaction, meta-organizational.

### F5 -- Agent count regime
Single agent, small team, large fleet, cross-organizational, unspecified.

### F6 -- Failure relevance
Describes a failure, analyzes a failure, proposes a preventive control, proposes a detective control, proposes a corrective control, evaluates control effectiveness.

### F7 -- Control type
Technical, procedural, economic, legal, social.

### F8 -- Source independence
Independent academic, independent practitioner, model provider, tooling vendor, self-study by subject organization, funded by subject, undisclosed.

### F9 -- Maturity of subject
Theoretical proposal, prototype, limited deployment, production at scale, deprecated.

### F10 -- Temporal relevance
Foundational, current, dated but instructive, superseded by capability change.

### F11 -- Stakeholder perspective
Operator, overseer, affected external party, regulator, adversary, agent developer, researcher.

### F12 -- Applicability
Directly actionable, adaptable with modification, background, comparative reference only.

---

## Exclusion register

What was removed from v2 and why. Kept explicit so the boundary is contestable rather than invisible.

| Removed | Reason |
|---|---|
| Voting mechanism design (quadratic, conviction, futarchy, sortition) | Unchanged by agent presence. Pointer retained at 15.1. |
| Commons governance, institutional economics depth | Foundational but not agent-specific. Compressed to 15.3. |
| Political theory, social choice, deliberative democracy | Human collective decision theory. Compressed to 15.1. |
| Grants program design detail | Retained only where agents evaluate or allocate (section 8.2). |
| Token design, monetary policy, market microstructure | Financial engineering, not organizational autonomy. |
| Cooperatives, standards bodies, scientific institutions, religious governance, HOAs | Adjacent institutions without delegated machine authority. |
| Participation equity, inclusion, cultural studies | Human community dynamics; relevant to DAOs, not to what makes an organization agentic. |
| DAO empirical studies (turnout, concentration, delegation networks) | Retained only as method precedent; superseded by 16.1. |
| Tax, IP, securities regulation | General entity concerns. Retained only where agent action creates novel exposure (12.6.3). |

**Judgment calls worth revisiting.** Three exclusions are genuinely arguable. Reputation and sybil resistance were cut to a pointer, but if agents accrue governance weight, that literature becomes load-bearing rather than background. Token design was cut entirely, though incentive alignment for agent operators may pull parts of it back. And participation equity was cut as human-community material, but if agents mediate access to participation, exclusion effects become an agentic design question rather than a social one.

---

## Notes on use

**The tree is now roughly 480 nodes, down from 700, with more depth in fewer places.** Sections 2, 4, 6, 10, and 11 carry the weight. Sections 15 and 16 are intentionally shallow.

**Section 6 is the thinnest literature and the highest leverage.** Treating agents as organizational members -- selection, performance management, promotion, retirement -- has almost no published research, but the operational questions arrive immediately in practice. If the library is meant to support building rather than only surveying, this is where original work would be most valuable.

**Section 11 is a coding scheme, not a set of shelves.** Most nodes will hold one or two postmortems. Its value is at design time: reading the failure list before deploying, not after.

**Section 12.1 remains the unsolved core.** Everything in sections 2 through 10 presupposes someone accountable for setting policy and responding to incidents. That the section exists and is mostly empty is the honest state of the field.
