// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title  RouteClerkGate
/// @notice On-chain accountability gate for agents that trade on Elysium and HyperCore.
///
///         The mechanic is one line:
///
///             Route Commitment  ->  Fill  ->  Autopsy  ->  Act or Blocked
///
///         An agent must commit to a route and its expected all-in cost BEFORE it
///         may act. After the fill lands (via ElysiumCoreWriter), the Clerk files an
///         Autopsy grading realized cost against the commitment. If the deviation
///         breaches the threshold, the agent's next action is refused until the
///         Autopsy is acknowledged or the deviation is covered with a bond.
///
///         Custody is untouched: this contract never holds or moves the user's
///         trading funds. It only gates the agent's ability to open new risk.
///
/// @dev    Prototype for the Elysium / Ascend builder submission. Design intent for
///         production:
///           - commitments are keyed by a keccak256 digest computed off-chain by the
///             Clerk (agent, intent, route, expected cost, deadline);
///           - the integrating agent calls {act} (or reads {canAct}) immediately
///             before dispatching an order through ElysiumCoreWriter;
///           - Autopsy inputs (realized cost, funding/position drift) come from a
///             RouteClerkAdapter that reads Elysium's HyperCore market-data precompile
///             once it is live (~4 weeks after mainnet). Until then the Clerk operator
///             files them, and the gate logic is identical.
contract RouteClerkGate {
    struct Commitment {
        address agent;
        bytes32 routeHash;       // hash of chosen venue + parameters
        int256  expectedCostBps; // committed all-in cost vs mid, in bps
        uint256 sizeUsd;         // order notional
        uint64  deadline;        // commitment must be filled before this
        bool    filled;
    }

    struct Autopsy {
        bytes32 commitmentId;
        int256  realizedCostBps;
        int256  deviationBps;    // realized - expected (+ funding/drift)
        bool    passed;
        bool    acknowledged;
        bool    covered;
    }

    /// @notice Operator authorized to file Autopsies (RouteClerk's Clerk signer).
    address public clerk;

    mapping(bytes32 => Commitment) public commitments;
    mapping(bytes32 => Autopsy)    public autopsies;

    /// @notice agent => id of the failed Autopsy currently blocking it (0 = clear).
    mapping(address => bytes32) public openAutopsy;

    event CommitmentSubmitted(
        bytes32 indexed id,
        address indexed agent,
        bytes32 routeHash,
        int256  expectedCostBps,
        uint256 sizeUsd,
        uint64  deadline
    );
    event AutopsySubmitted(
        bytes32 indexed id,
        bytes32 indexed commitmentId,
        address indexed agent,
        int256  realizedCostBps,
        int256  deviationBps,
        bool    passed
    );
    event AgentBlocked(address indexed agent, bytes32 autopsyId, int256 deviationBps);
    event AgentUnblocked(address indexed agent, bytes32 autopsyId, bool covered);
    event DeviationCovered(address indexed agent, bytes32 autopsyId, uint256 bond);

    modifier onlyClerk() {
        require(msg.sender == clerk, "RouteClerk: caller is not the clerk");
        _;
    }

    constructor(address _clerk) {
        require(_clerk != address(0), "RouteClerk: clerk is zero");
        clerk = _clerk;
    }

    /// @notice Rotate the Clerk signer (agent operator / RouteClerk service).
    function setClerk(address _clerk) external onlyClerk {
        require(_clerk != address(0), "RouteClerk: clerk is zero");
        clerk = _clerk;
    }

    // ---------------------------------------------------------------------
    // 1. Route Commitment  — the agent promises a route and a cost
    // ---------------------------------------------------------------------

    /// @notice Commit to a route and its expected cost BEFORE acting.
    /// @param id               keccak256 digest computed by the Clerk
    /// @param routeHash        venue + parameters hash (HyperCore book vs Elysium AMM)
    /// @param expectedCostBps  committed all-in cost vs mid, in bps
    /// @param sizeUsd          order notional in USD
    /// @param deadline         unix seconds by which the fill must land
    function submitCommitment(
        bytes32 id,
        bytes32 routeHash,
        int256  expectedCostBps,
        uint256 sizeUsd,
        uint64  deadline
    ) external {
        require(commitments[id].agent == address(0), "RouteClerk: commitment exists");
        require(deadline > block.timestamp, "RouteClerk: deadline in the past");
        commitments[id] = Commitment({
            agent: msg.sender,
            routeHash: routeHash,
            expectedCostBps: expectedCostBps,
            sizeUsd: sizeUsd,
            deadline: deadline,
            filled: false
        });
        emit CommitmentSubmitted(id, msg.sender, routeHash, expectedCostBps, sizeUsd, deadline);
    }

    // ---------------------------------------------------------------------
    // 2. Gate — the ONE question the order path asks before it acts
    // ---------------------------------------------------------------------

    /// @notice True when the agent has no outstanding failed Autopsy.
    function canAct(address agent) public view returns (bool) {
        return openAutopsy[agent] == bytes32(0);
    }

    /// @notice Call immediately before dispatching an order through ElysiumCoreWriter.
    ///         Reverts while the agent is blocked, so the send never happens.
    function act(address agent) external view {
        require(canAct(agent), "RouteClerk: agent blocked by failed autopsy");
    }

    // ---------------------------------------------------------------------
    // 3. Autopsy — grade the fill against the commitment
    // ---------------------------------------------------------------------

    /// @notice File the Autopsy after the fill lands.
    /// @param id             unique autopsy id
    /// @param commitmentId   the commitment being graded
    /// @param realizedCostBps realized all-in cost vs mid, in bps
    /// @param fundingDriftBps funding/position drift since commitment, in bps
    /// @param thresholdBps   allowed deviation before the agent is blocked
    function submitAutopsy(
        bytes32 id,
        bytes32 commitmentId,
        int256  realizedCostBps,
        int256  fundingDriftBps,
        int256  thresholdBps
    ) external onlyClerk {
        Commitment storage cm = commitments[commitmentId];
        require(cm.agent != address(0), "RouteClerk: unknown commitment");
        require(autopsies[id].commitmentId == bytes32(0), "RouteClerk: autopsy exists");

        int256 deviation = realizedCostBps - cm.expectedCostBps + fundingDriftBps;
        bool passed = deviation <= thresholdBps;

        autopsies[id] = Autopsy({
            commitmentId: commitmentId,
            realizedCostBps: realizedCostBps,
            deviationBps: deviation,
            passed: passed,
            acknowledged: false,
            covered: false
        });
        cm.filled = true;

        emit AutopsySubmitted(id, commitmentId, cm.agent, realizedCostBps, deviation, passed);

        if (!passed) {
            openAutopsy[cm.agent] = id;
            emit AgentBlocked(cm.agent, id, deviation);
        }
    }

    // ---------------------------------------------------------------------
    // 4. Unblock — acknowledge the Autopsy, or cover the deviation
    // ---------------------------------------------------------------------

    /// @notice Acknowledge a failed Autopsy. Reopens the gate for the next action.
    function acknowledgeAutopsy(bytes32 id) external {
        Autopsy storage a = autopsies[id];
        require(a.commitmentId != bytes32(0), "RouteClerk: unknown autopsy");
        address agent = commitments[a.commitmentId].agent;
        require(openAutopsy[agent] == id, "RouteClerk: autopsy not blocking");
        a.acknowledged = true;
        openAutopsy[agent] = bytes32(0);
        emit AgentUnblocked(agent, id, false);
    }

    /// @notice Cover the deviation with a bond. The bond is claimable by a
    ///         specialist who proves the Autopsy was correct (challenge market —
    ///         post-launch roadmap). Reopens the gate.
    function coverDeviation(bytes32 id) external payable {
        Autopsy storage a = autopsies[id];
        require(a.commitmentId != bytes32(0), "RouteClerk: unknown autopsy");
        require(msg.value > 0, "RouteClerk: bond required");
        address agent = commitments[a.commitmentId].agent;
        require(openAutopsy[agent] == id, "RouteClerk: autopsy not blocking");
        a.covered = true;
        openAutopsy[agent] = bytes32(0);
        emit DeviationCovered(agent, id, msg.value);
        emit AgentUnblocked(agent, id, true);
    }

    // ---------------------------------------------------------------------
    // Views for dashboards / agents
    // ---------------------------------------------------------------------

    function commitmentOf(bytes32 id) external view returns (Commitment memory) {
        return commitments[id];
    }

    function autopsyOf(bytes32 id) external view returns (Autopsy memory) {
        return autopsies[id];
    }
}
