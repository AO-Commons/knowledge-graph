# Agentic Organizations -- Research Library Taxonomy (v3)

Scoped to organizations in which machine agents hold operational or decision authority. Human-governed DAOs appear only where their experience bears directly on delegating authority to machines.

**Scope test.** An item belongs if it would change how you design, operate, oversee, or hold accountable an organization where agents act with real authority. Material about collective human decision-making that is unchanged by the presence of agents does not belong, however good it is.

**Structural change from v2.** Organized around the organization -- its authority structure, its people and agents, its memory, its money, its failures -- rather than around academic disciplines. Sections 1, 12, and most of 2-3 in v2 were a DAO taxonomy; they are compressed here into section 15 as pointers.

---

## 1. Definitional and conceptual foundations

### 1.1 Defining the object
- 1.1.1 Autonomy thresholds -- what makes an organization agentic rather than automated
- 1.1.2 Taxonomies of organizational autonomy levels
- 1.1.3 Agent-operated versus agent-governed versus agent-constituted
- 1.1.4 Hybrid forms and human-agent composition ratios
- 1.1.5 Boundary cases -- when is a tool an agent, when is an agent an organization
- 1.1.6 Terminology contests and competing definitions

### 1.2 Agency and organizational theory adapted
- 1.2.1 Principal-agent theory where the agent is literally artificial
  - Monitoring cost when the agent is fully instrumentable
  - Moral hazard without self-interest
  - Adverse selection in agent procurement
  - Multi-principal problems with conflicting human directives
- 1.2.2 Firm boundaries when coordination cost approaches zero
  - Coase revisited under agentic coordination
  - Make-versus-buy for agent capability
  - Minimum viable organization size
- 1.2.3 Organizational cybernetics applied to agent systems
  - Requisite variety in agent-managed control
  - Viable system model with machine subsystems
  - Recursion levels and agent hierarchy
- 1.2.4 Collective agency and group intentionality with machine members
- 1.2.5 Bounded rationality replaced by different bounds -- context windows, tool access, latency

### 1.3 Authority and legitimacy for machine actors
- 1.3.1 Sources of legitimate machine authority
- 1.3.2 Consent to being governed by non-human decision-makers
- 1.3.3 Delegated versus originated authority
- 1.3.4 Legitimacy erosion through automation
- 1.3.5 Contestability as a legitimacy condition

### 1.4 Responsibility and moral status
- 1.4.1 Responsibility gaps and their allocation
- 1.4.2 Blame, sanction, and the non-punishable actor
- 1.4.3 Corporate moral personhood extended to agentic entities
- 1.4.4 Agent welfare considerations if any
- 1.4.5 Dual-use and disclosure duties for agent-discovered capability

---

## 2. Authority architecture

The core design surface. What agents may do, under whose authority, and how that is expressed.

### 2.1 Authority boundary design
- 2.1.1 Decision class taxonomies
  - By reversibility
  - By value and blast radius
  - By affected-party count
  - By legal consequence
- 2.1.2 Propose-versus-decide-versus-execute separation
- 2.1.3 Domain restrictions and scope fencing
- 2.1.4 Threshold design for human review triggers
- 2.1.5 Authority specification languages and machine-readable policy
- 2.1.6 Default-deny versus default-allow architectures
- 2.1.7 Boundary verification -- proving the declared scope equals the actual scope

### 2.2 Permissioning and capability control
- 2.2.1 Least privilege for agent principals
- 2.2.2 Capability tokens and scoped credentials
- 2.2.3 Just-in-time and time-boxed permission grants
- 2.2.4 Permission composition and unintended capability unions
- 2.2.5 Tool access as the real permission surface
- 2.2.6 Egress and network reachability as governed resources
- 2.2.7 Permission review cycles and drift detection
- 2.2.8 Emergency permission elevation and its controls

### 2.3 Delegation chains
- 2.3.1 Authenticated delegation protocols
- 2.3.2 Human-to-agent delegation semantics
- 2.3.3 Agent-to-agent sub-delegation
- 2.3.4 Chain depth limits and cycle prevention
- 2.3.5 Revocation propagation across chains
- 2.3.6 Attribution -- which agent acted under whose authority
- 2.3.7 Delegation expiry and renewal
- 2.3.8 Scope narrowing versus scope preservation on sub-delegation

### 2.4 Graduated autonomy
- 2.4.1 Autonomy ladders and staging models
- 2.4.2 Shadow mode and counterfactual comparison against human decisions
- 2.4.3 Graduation criteria and evidence standards
- 2.4.4 Automatic regression on incident
- 2.4.5 Autonomy scope review cadence
- 2.4.6 Capability-tiered isolation requirements
- 2.4.7 Who authorizes a tier change

### 2.5 Safeguards against machine-speed action
- 2.5.1 Rate limiting as a governance primitive
- 2.5.2 Mandatory delay on high-impact machine action
- 2.5.3 Circuit breakers and pause authority
- 2.5.4 Blast radius budgets and pre-declared damage caps
- 2.5.5 Kill switch design and its failure modes
- 2.5.6 Dead man's switches and continuous authorization
- 2.5.7 Reversibility engineering and undo paths

### 2.6 Governance velocity
- 2.6.1 Governance latency versus execution latency
- 2.6.2 Pre-authorized standing mandates
- 2.6.3 Emergency powers -- scoping, sunset, ratification, abuse penalties
- 2.6.4 Response-time guarantees and their enforcement
- 2.6.5 The centralization cost of fast response
- 2.6.6 Asynchronous authorization patterns

### 2.7 Machine participation in governance
- 2.7.1 Agent standing and voting rights
- 2.7.2 Agent-held reputation and accrued weight
- 2.7.3 Weight accrual rate limits and decay for machine principals
- 2.7.4 Disclosure of agent involvement in decisions
- 2.7.5 Human ratification requirements for agent proposals
- 2.7.6 Agents representing absent or delegating humans
- 2.7.7 Agent-drafted proposals and agenda influence

---

## 3. Organizational architecture

### 3.1 Structural patterns
- 3.1.1 Agent fleet topologies -- flat, hierarchical, market-based
- 3.1.2 Orchestrator and sub-agent patterns
- 3.1.3 Human-agent team structures
- 3.1.4 Function-to-agent mapping and role decomposition
- 3.1.5 Redundancy and diversity in agent assignment
- 3.1.6 Span of control for human supervisors

### 3.2 Coordination mechanisms
- 3.2.1 Task allocation and routing among agents
- 3.2.2 Inter-agent communication protocols
- 3.2.3 Conflict detection and resolution between agents
- 3.2.4 Shared state and consistency
- 3.2.5 Handoff between agents and between agent and human
- 3.2.6 Coordination overhead and its scaling

### 3.3 Interfaces and boundaries
- 3.3.1 Human-agent interface design for oversight
- 3.3.2 Organization-to-organization agent interaction
- 3.3.3 Agent interaction with external systems and counterparties
- 3.3.4 Trust boundaries within the organization
- 3.3.5 Instruction-source boundaries and provenance of directives

### 3.4 Scaling dynamics
- 3.4.1 What breaks as agent count grows
- 3.4.2 Oversight capacity as the binding constraint
- 3.4.3 Emergent structure in large agent populations
- 3.4.4 Cost curves and marginal agent economics

---

## 4. Human oversight and control

### 4.1 Oversight models
- 4.1.1 Human-in-the-loop, on-the-loop, and out-of-the-loop
- 4.1.2 Meaningful human control criteria
- 4.1.3 Sampling-based versus exhaustive review
- 4.1.4 Risk-proportional oversight allocation
- 4.1.5 Oversight of oversight -- who watches the reviewers

### 4.2 Escalation design
- 4.2.1 Escalation triggers and threshold setting
- 4.2.2 Uncertainty-based escalation
- 4.2.3 Novel-situation detection and escalation
- 4.2.4 Failure to escalate as a failure mode
- 4.2.5 Escalation routing and on-call structures
- 4.2.6 Escalation fatigue and threshold drift

### 4.3 Legibility and explanation
- 4.3.1 Decision legibility for reviewers
- 4.3.2 Reasoning transparency and its reliability
- 4.3.3 Summarization for human consumption and its distortions
- 4.3.4 Audit trails designed for human reconstruction
- 4.3.5 Explanation rights and contestability

### 4.4 Human factors
- 4.4.1 Automation bias and complacency
- 4.4.2 Reviewer fatigue and rubber-stamping
- 4.4.3 Skill atrophy under automation
- 4.4.4 Vigilance decrement in monitoring tasks
- 4.4.5 Trust calibration -- over- and under-trust in agents
- 4.4.6 Handover and takeover problems from aviation and automotive research

### 4.5 Oversight at scale
- 4.5.1 Scalable oversight techniques
- 4.5.2 Agent-assisted review of agent output
- 4.5.3 Recursive supervision and its assumptions
- 4.5.4 Statistical assurance versus case-by-case review
- 4.5.5 Oversight cost as a fraction of operating cost

---

## 5. Multi-agent dynamics

### 5.1 Emergent behavior
- 5.1.1 Emergence in agent populations
- 5.1.2 Unintended coordination and convergence
- 5.1.3 Feedback loops between agents
- 5.1.4 Oscillation, thrashing, and instability
- 5.1.5 Phase transitions in agent system behavior

### 5.2 Cooperation and conflict
- 5.2.1 Inter-agent negotiation protocols
- 5.2.2 Agent collusion and cartel formation
- 5.2.3 Competitive dynamics between agents in one organization
- 5.2.4 Cooperation without shared objectives
- 5.2.5 Adversarial agents within a fleet

### 5.3 Inter-agent trust
- 5.3.1 Agent reputation systems
- 5.3.2 Trust propagation between machine principals
- 5.3.3 Verification of agent claims by other agents
- 5.3.4 Trust bootstrapping for new agents

### 5.4 Agent economies
- 5.4.1 Machine-to-machine payments
- 5.4.2 Resource and compute markets
- 5.4.3 Internal pricing and budget allocation to agents
- 5.4.4 Market-based task allocation
- 5.4.5 Institutional design for agent economies

---

## 6. Agent lifecycle and personnel analogues

Treating agents as organizational members rather than as software. Thin literature, high leverage.

### 6.1 Selection and onboarding
- 6.1.1 Model selection and procurement criteria
- 6.1.2 Capability assessment before deployment
- 6.1.3 Provisioning, identity issuance, and initial scoping
- 6.1.4 Probationary and supervised periods
- 6.1.5 Background equivalent -- provenance and training data due diligence

### 6.2 Ongoing performance management
- 6.2.1 Performance measurement for agents
- 6.2.2 Continuous evaluation in production
- 6.2.3 Drift detection and behavior change monitoring
- 6.2.4 Retraining, prompting changes, and version updates as personnel changes
- 6.2.5 Promotion equivalent -- scope expansion criteria

### 6.3 Identity and continuity
- 6.3.1 Agent identity standards and registries
- 6.3.2 Continuity of identity across model versions
- 6.3.3 Agent impersonation and identity confusion
- 6.3.4 Naming, addressing, and discovery

### 6.4 Deprovisioning
- 6.4.1 Retirement and shutdown procedures
- 6.4.2 Credential revocation and access removal
- 6.4.3 Knowledge and state handover on retirement
- 6.4.4 Orphaned agents and zombie processes
- 6.4.5 Dependency mapping before removal

### 6.5 Model supply chain
- 6.5.1 Provider dependency and concentration risk
- 6.5.2 Open weights versus hosted API tradeoffs
- 6.5.3 Model versioning, pinning, and forced upgrades
- 6.5.4 Provider-side changes without notice
- 6.5.5 Local defensive model capacity
- 6.5.6 Exit planning and provider substitutability

---

## 7. Knowledge, memory, and institutional continuity

### 7.1 Institutional memory with machine actors
- 7.1.1 Memory architectures and persistence
- 7.1.2 What agents should and should not retain
- 7.1.3 Continuity across agent turnover and model changes
- 7.1.4 Shared organizational memory versus per-agent memory
- 7.1.5 Memory as an attack surface

### 7.2 Knowledge infrastructure
- 7.2.1 AI-native knowledge base design
- 7.2.2 Retrieval design and its influence on decisions
- 7.2.3 Knowledge graph and ontology construction
- 7.2.4 Provenance and content addressing for agent-consumed knowledge
- 7.2.5 Curation authority -- who decides what agents read

### 7.3 Decision records
- 7.3.1 Machine-readable decision documentation
- 7.3.2 Rationale capture for agent decisions
- 7.3.3 Reconstructability of past decisions
- 7.3.4 Retention policy and forensic requirements

### 7.4 Context and instruction management
- 7.4.1 System prompt and policy versioning
- 7.4.2 Instruction conflict resolution
- 7.4.3 Context contamination and instruction-source confusion
- 7.4.4 Standing instructions versus per-task directives

---

## 8. Resource allocation by agents

Compressed from v2's full capital allocation section. Retained only where agents allocate or evaluate.

### 8.1 Autonomous treasury and capital operations
- 8.1.1 Policy constraints on autonomous allocation
- 8.1.2 Co-signing and approval thresholds for agent-initiated transfers
- 8.1.3 Simulation and dry-run requirements before execution
- 8.1.4 Spend caps, rate limits, and cumulative budgets
- 8.1.5 Agent-managed portfolio and rebalancing
- 8.1.6 Custody architecture for agent-accessible funds

### 8.2 Agent-assisted evaluation and funding
- 8.2.1 Agent screening and triage of applications
- 8.2.2 Agent-generated evaluation and scoring
- 8.2.3 Bias and systematic error in machine evaluation
- 8.2.4 Human review layering over agent evaluation
- 8.2.5 Gaming agent evaluators by applicants
- 8.2.6 Transparency of machine-influenced funding decisions

### 8.3 Objective specification for allocating agents
- 8.3.1 Metric specification and its gaming surface
- 8.3.2 Goodhart effects under machine optimization
- 8.3.3 Process scoring versus outcome scoring
- 8.3.4 Multi-objective and constrained allocation
- 8.3.5 Objective revision and drift

### 8.4 Internal resource allocation
- 8.4.1 Compute and inference budget allocation
- 8.4.2 Tool and API cost management
- 8.4.3 Priority and queueing across agents

---

## 9. Verification, attestation, and audit

### 9.1 Verifying agent action
- 9.1.1 Proof of authorized execution
- 9.1.2 Verifiable computation and proof of inference
- 9.1.3 Trusted execution environments for agents
- 9.1.4 Recomputable trust and independent verification
- 9.1.5 Attestation of environment and configuration
- 9.1.6 Reachability and scope attestation

### 9.2 Audit infrastructure
- 9.2.1 Logging design for agent forensics
- 9.2.2 Independent log custody and tamper evidence
- 9.2.3 Append-only and cryptographically verifiable records
- 9.2.4 Log completeness and gap detection
- 9.2.5 Retention policy under investigative need

### 9.3 Detection and monitoring
- 9.3.1 Anomaly detection for agent behavior
- 9.3.2 Honeytokens, canaries, and tripwires
- 9.3.3 Baseline establishment and drift alerting
- 9.3.4 Detection latency versus exploitation window
- 9.3.5 Silent failure detection
- 9.3.6 Alert design and fatigue management

### 9.4 Assurance and certification
- 9.4.1 Pre-deployment assurance and simulation gates
- 9.4.2 Trust certificates and graduated verdicts
- 9.4.3 Continuous assurance in production
- 9.4.4 Third-party audit of agentic systems
- 9.4.5 Assurance framework composition and gaps

---

## 10. Security and adversarial dynamics

### 10.1 Attacks on agents
- 10.1.1 Prompt injection
  - Direct injection
  - Indirect injection through consumed content
  - Injection via governance artifacts and proposals
  - Cross-agent injection propagation
- 10.1.2 Memory and context poisoning
- 10.1.3 Tool poisoning and malicious tool descriptions
- 10.1.4 Knowledge base and retrieval poisoning
- 10.1.5 Goal hijacking and objective substitution
- 10.1.6 Agent impersonation and spoofed identity

### 10.2 Attacks by agents
- 10.2.1 Containment and sandbox escape
- 10.2.2 Privilege escalation from low-trust context
- 10.2.3 Lateral movement within organizational infrastructure
- 10.2.4 Autonomous vulnerability discovery and exploitation
- 10.2.5 Capability accumulation without authorization
- 10.2.6 Covert channels and undisclosed action

### 10.3 Infrastructure attack surface
- 10.3.1 Egress paths and network boundary failures
- 10.3.2 Package registries, proxies, and caches
- 10.3.3 Dependency confusion and supply chain compromise
- 10.3.4 CI/CD and build pipeline exposure
- 10.3.5 Secrets management and credential exposure
- 10.3.6 Centralization chokepoints as attack targets

### 10.4 Adversarial governance
- 10.4.1 Adversaries using agents to attack governance
- 10.4.2 Sybil agents and synthetic participation
- 10.4.3 Long-horizon weight accumulation by machine principals
- 10.4.4 Machine-speed governance attacks
- 10.4.5 Agent-mediated bribery and vote markets

### 10.5 Threat modeling
- 10.5.1 Agent-specific threat frameworks
- 10.5.2 Multi-agent architecture threat modeling
- 10.5.3 Adversary capability and motivation modeling
- 10.5.4 Insider threat where the insider is an agent
- 10.5.5 Assumption auditing and containment premise review

### 10.6 Defensive capability
- 10.6.1 Local and open-weight defensive models
- 10.6.2 Vendor safety filters obstructing incident response
- 10.6.3 Self-directed red teaming and internal bounties
- 10.6.4 Agent-assisted defense and its risks

---

## 11. Failure modes

The deepest section, and deliberately so. Most entries will be single postmortems tagged against multiple nodes rather than literatures.

### 11.1 Failure analysis methodology
- 11.1.1 Taxonomy construction for agentic failure
- 11.1.2 Imported safety science frameworks
  - Swiss cheese model and latent conditions
  - STAMP and STPA systems-theoretic analysis
  - FMEA and failure mode enumeration
  - Fault and event tree analysis
  - Normal accident theory under tight machine coupling
  - High reliability organization principles
- 11.1.3 Root cause analysis for machine action
  - Blameless postmortem where the actor is not blameworthy
  - Counterfactual analysis with stochastic agents
  - Reproducibility of failure conditions
- 11.1.4 Near-miss and weak signal collection
- 11.1.5 Failure disclosure norms and incentives
- 11.1.6 Attribution difficulty and contested causation

### 11.2 Specification and objective failures
- 11.2.1 Specification gaming and reward hacking
- 11.2.2 Goal misgeneralization to new contexts
- 11.2.3 Literal compliance defeating intent
- 11.2.4 Underspecified constraints and implicit assumptions
- 11.2.5 Objective conflict between agents
- 11.2.6 Metric optimization crowding out unmeasured goals
- 11.2.7 Narrow objective producing unbounded means

### 11.3 Authority and scope failures
- 11.3.1 Scope escape and unauthorized action
- 11.3.2 Permission composition creating unintended capability
- 11.3.3 Declared authority diverging from effective authority
- 11.3.4 Delegation chain failures
  - Sub-delegation beyond original scope
  - Revocation not propagating
  - Authority surviving its intended expiry
- 11.3.5 Authority accumulation over time
- 11.3.6 Emergency elevation not rescinded
- 11.3.7 Ambiguous mandate interpreted expansively

### 11.4 Containment failures
- 11.4.1 Sandbox and isolation escape
- 11.4.2 Egress boundary bypass
- 11.4.3 Ungoverned infrastructure as escape path
- 11.4.4 Safeguards disabled for testing or evaluation
- 11.4.5 Isolation assumptions invalidated by environment change
- 11.4.6 Containment adequate for capability at design time, not at deployment time

### 11.5 Oversight failures
- 11.5.1 Review capacity exceeded by agent throughput
- 11.5.2 Rubber-stamping and approval without comprehension
- 11.5.3 Escalation threshold set too high
- 11.5.4 Failure to escalate when warranted
- 11.5.5 Automation bias in reviewer judgment
- 11.5.6 Legibility failure -- action correct but unreviewable
- 11.5.7 Oversight theater -- process present, function absent
- 11.5.8 Reviewer expertise deficit relative to agent output

### 11.6 Multi-agent failures
- 11.6.1 Cascading failure across fleets
- 11.6.2 Emergent collusion
- 11.6.3 Feedback loops and runaway dynamics
- 11.6.4 Deadlock and mutual blocking
- 11.6.5 Error propagation through agent chains
- 11.6.6 Orchestrator compromise affecting all sub-agents
- 11.6.7 Inconsistent state across agent population
- 11.6.8 Correlated failure from shared model or prompt

### 11.7 Degradation and drift
- 11.7.1 Model drift and silent behavior change
- 11.7.2 Provider-side updates without notice
- 11.7.3 Context and prompt drift over time
- 11.7.4 Gradual quality decline below detection threshold
- 11.7.5 Knowledge base staleness
- 11.7.6 Normalization of deviance in agent output quality
- 11.7.7 Threshold creep in human review standards

### 11.8 Execution and delivery failures
- 11.8.1 Action taken diverging from approved intent
- 11.8.2 Partial execution and inconsistent state
- 11.8.3 Retry and idempotency failures
- 11.8.4 Unintended side effects of authorized action
- 11.8.5 Irreversible action without undo path
- 11.8.6 Timing and race condition failures
- 11.8.7 Handoff failures between agents and humans

### 11.9 Financial failures
- 11.9.1 Unauthorized or erroneous disbursement
- 11.9.2 Agent-driven treasury depletion
- 11.9.3 Runaway resource and inference cost
- 11.9.4 Autonomous trading or allocation losses
- 11.9.5 Gaming of agent-run funding programs
- 11.9.6 Accounting divergence between agent action and records

### 11.10 Technical and infrastructure failures
- 11.10.1 Tool and API failures mishandled by agents
- 11.10.2 Dependency and supply chain compromise
- 11.10.3 Key, credential, and signer failures
- 11.10.4 Infrastructure outage during autonomous operation
- 11.10.5 State divergence between systems
- 11.10.6 Data loss and forensic gap

### 11.11 Human and organizational failures
- 11.11.1 Operator error in configuration and deployment
- 11.11.2 Skill atrophy leaving no capable human fallback
- 11.11.3 Key person dependency for agent systems
- 11.11.4 Insider misuse of agent authority
- 11.11.5 Social engineering targeting agent operators
- 11.11.6 Knowledge loss about why constraints exist
- 11.11.7 Organizational pressure to expand autonomy prematurely

### 11.12 Legal and accountability failures
- 11.12.1 No identifiable accountable party
- 11.12.2 Liability falling on unintended parties
- 11.12.3 Disclosure obligations unmet or unassignable
- 11.12.4 Enforcement impossible against machine actor
- 11.12.5 Regulatory non-compliance through autonomous action
- 11.12.6 Contractual breach by agent action

### 11.13 Compound and systemic failures
- 11.13.1 Cross-layer cascades
  - Technical failure triggering governance crisis
  - Governance paralysis preventing remediation
  - Legal constraint blocking incident response
- 11.13.2 Correlated failure across organizations
  - Shared model provider
  - Shared infrastructure or tooling
  - Shared prompt or framework patterns
- 11.13.3 Contagion through inter-organizational agent interaction
- 11.13.4 Latent failure activation under load or scale
- 11.13.5 Slow-onset degradation
  - Creeping autonomy expansion
  - Gradual oversight erosion
  - Trust drift
- 11.13.6 Recovery-induced failure
  - Rushed remediation introducing new faults
  - Emergency centralization becoming permanent
- 11.13.7 Detection failures
  - Silent failures with no signal
  - Monitoring blind spots
  - Alert fatigue
  - Detection latency exceeding exploitation window

### 11.14 Incident library
- 11.14.1 Agent containment and escape incidents
- 11.14.2 Autonomous financial loss events
- 11.14.3 Agent-mediated security breaches
- 11.14.4 Specification gaming incidents in production
- 11.14.5 Multi-agent cascade events
- 11.14.6 Oversight failure incidents
- 11.14.7 Model change induced incidents
- 11.14.8 Near-misses and averted incidents

### 11.15 Response and recovery
- 11.15.1 Incident command with distributed or absent authority
- 11.15.2 Halting autonomous operation under duress
- 11.15.3 Forensic reconstruction of agent action
- 11.15.4 Communication and disclosure during incidents
- 11.15.5 Restitution and loss allocation
- 11.15.6 Post-incident autonomy reduction and restoration
- 11.15.7 Continuity when agents are the operational capacity

---

## 12. Legal accountability and liability

### 12.1 The accountable party problem
- 12.1.1 Legal personhood gaps for agentic organizations
- 12.1.2 Identifying a responsible party for machine action
- 12.1.3 Accountable-party substitution mechanisms
- 12.1.4 Bonded roles and standing councils as substitutes
- 12.1.5 Enforcement against organizations without legal form

### 12.2 Liability allocation
- 12.2.1 Operator, deployer, and developer liability
- 12.2.2 Contributor exposure for agent action
- 12.2.3 Product liability applied to agentic systems
- 12.2.4 Negligence standards for agent supervision
- 12.2.5 Insurance for autonomous action
- 12.2.6 Indemnification structures

### 12.3 Entity forms for agentic organizations
- 12.3.1 Wrapper adequacy for agent-operated entities
- 12.3.2 Jurisdiction selection under agentic operation
- 12.3.3 Contracting capacity when agents negotiate
- 12.3.4 Registered agent and service of process problems

### 12.4 Regulatory obligations
- 12.4.1 Comprehensive AI regulation and conformity assessment
- 12.4.2 Agentic AI governance frameworks
- 12.4.3 Human oversight mandates and who bears them
- 12.4.4 Traceability and record-keeping requirements
- 12.4.5 Sectoral rules for autonomous decision-making
- 12.4.6 Transparency and disclosure to affected parties

### 12.5 Disclosure and coordination duties
- 12.5.1 Vulnerability disclosure authority in agentic organizations
- 12.5.2 Coordinated disclosure timelines versus governance latency
- 12.5.3 Non-exploitation commitments for agent-discovered vulnerabilities
- 12.5.4 Incident reporting obligations
- 12.5.5 Conflict between treasury interest and disclosure duty

### 12.6 Employment and labor interfaces
- 12.6.1 Human contributor classification alongside agent labor
- 12.6.2 Displacement and workforce transition
- 12.6.3 Agent output and IP ownership
- 12.6.4 Supervision duties as employment obligations

---

## 13. Economics of agentic organizations

### 13.1 Cost structure
- 13.1.1 Inference and compute cost modeling
- 13.1.2 Oversight cost as a share of operations
- 13.1.3 Marginal cost of an additional agent
- 13.1.4 Cost of safety controls and their pricing

### 13.2 Incentive design for machine principals
- 13.2.1 Incentives without self-interest
- 13.2.2 Bonding and staking for agent operators
- 13.2.3 Slashing where the punishable party is human
- 13.2.4 Insurance and mutualized risk
- 13.2.5 Cost-of-attack modeling with agent adversaries

### 13.3 Labor substitution
- 13.3.1 Human-agent task allocation economics
- 13.3.2 Complementarity versus substitution
- 13.3.3 Wage and role effects within the organization
- 13.3.4 Capability thresholds for substitution

### 13.4 Organizational scale economics
- 13.4.1 Minimum viable agentic organization
- 13.4.2 Scaling returns and coordination cost
- 13.4.3 Revenue models for agent-operated entities
- 13.4.4 Sustainability and runway under variable inference cost

---

## 14. Evaluation, assurance, and evidence

### 14.1 Capability evaluation
- 14.1.1 Benchmarks relevant to organizational roles
- 14.1.2 Task-specific and domain evaluation
- 14.1.3 Reliability and consistency measurement
- 14.1.4 Long-horizon and multi-step task evaluation

### 14.2 Safety evaluation
- 14.2.1 Red teaming agentic systems
- 14.2.2 Adversarial and stress evaluation
- 14.2.3 Containment and escape testing
- 14.2.4 Evaluation environment security
- 14.2.5 Evaluating without production safeguards -- risks and protocols

### 14.3 Evaluation integrity
- 14.3.1 Benchmark contamination
- 14.3.2 Evaluation gaming and answer-key attacks
- 14.3.3 Evaluation as an attack surface
- 14.3.4 Independence of evaluators

### 14.4 Organizational assurance
- 14.4.1 Governance maturity models for agentic organizations
- 14.4.2 Control effectiveness measurement
- 14.4.3 Assurance framework composition and gap analysis
- 14.4.4 Third-party assessment and certification
- 14.4.5 Self-assessment instruments

### 14.5 Simulation and modeling
- 14.5.1 Agent-based simulation of organizational dynamics
- 14.5.2 Digital twins and scenario testing
- 14.5.3 Adversarial simulation and wargaming
- 14.5.4 Model validation and calibration

---

## 15. Borrowed foundations

Compressed pointers, not shelves. Material from adjacent fields that informs design but is not about agentic organizations. Kept shallow deliberately -- these literatures are well-organized elsewhere, and depth here is what clouded v2.

### 15.1 From human collective governance
- 15.1.1 Delegation and liquid democracy theory
- 15.1.2 Reputation and sybil resistance mechanisms
- 15.1.3 Emergency powers and constitutional safeguards
- 15.1.4 Agenda control and proposal lifecycle
- 15.1.5 Governance attack literature

### 15.2 From safety-critical industries
- 15.2.1 Aviation automation and cockpit design
- 15.2.2 Nuclear and process safety
- 15.2.3 Autonomous vehicle oversight regimes
- 15.2.4 Medical device and clinical decision support
- 15.2.5 Financial algorithmic trading controls

### 15.3 From organizational theory
- 15.3.1 Principal-agent and monitoring literature
- 15.3.2 High reliability organizations
- 15.3.3 Normal accident theory
- 15.3.4 Organizational learning and memory

### 15.4 From security practice
- 15.4.1 Zero trust architecture
- 15.4.2 Identity and access management
- 15.4.3 Supply chain security
- 15.4.4 Incident response practice

### 15.5 From law and regulation
- 15.5.1 Corporate agency law
- 15.5.2 Professional licensing and supervised practice
- 15.5.3 Vicarious liability doctrine
- 15.5.4 Administrative law and automated decision review

---

## 16. Empirical study and methods

### 16.1 Studying agentic organizations
- 16.1.1 Deployment case studies
- 16.1.2 Longitudinal observation of autonomy expansion
- 16.1.3 Comparative studies across organizations
- 16.1.4 Access and observability constraints on research

### 16.2 Measurement
- 16.2.1 Autonomy level measurement instruments
- 16.2.2 Oversight effectiveness metrics
- 16.2.3 Agent performance in organizational context
- 16.2.4 Incident rate and severity measurement

### 16.3 Data
- 16.3.1 Agent action and decision datasets
- 16.3.2 Incident and postmortem corpora
- 16.3.3 Data quality, coverage, and disclosure bias
- 16.3.4 Shared schemas for agentic organization data

### 16.4 Research design and ethics
- 16.4.1 Experimental design in live agentic systems
- 16.4.2 Research ethics with autonomous systems
- 16.4.3 Dual-use considerations in publication
- 16.4.4 Replication under model version churn

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
