# DomoActors-Py Bank - Interactive Banking System

A comprehensive demonstration of the DomoActors framework showcasing supervision, hierarchical actors, and real-world patterns.

## Overview

DomoActors-Py Bank is a fully functional interactive banking system that demonstrates:

- **Actor Hierarchy**: Parent-child relationships with proper supervision
- **Multi-Step Coordination**: Transfer orchestration with retry logic
- **"Let It Crash" Philosophy**: Validation errors handled by supervision
- **Self-Messaging Pattern**: State changes via mailbox for consistency
- **Audit Trail**: Complete transaction history with refund tracking
- **Context-Aware Error Handling**: Detailed error messages based on operation type

## Features

### 8 Interactive Commands

1. **Open Account** - Create checking or savings accounts
2. **Deposit Funds** - Add money to accounts
3. **Withdraw Funds** - Remove money from accounts
4. **Transfer Funds** - Move funds between accounts with retry and refund
5. **Account Summary** - View formatted account details
6. **Transaction History** - Complete audit trail with refund reasons
7. **List All Accounts** - View all created accounts
8. **Pending Transfers** - Monitor transfers in progress

### Transfer Coordination

Transfers use a sophisticated 5-phase state machine:

1. **Immediate Withdrawal** - Funds withdrawn synchronously
2. **Record Pending** - Transfer marked as pending (async)
3. **Attempt Deposit** - Try to deposit to target account (async)
4. **Retry with Backoff** - Exponential backoff: 1s, 2s, 4s (max 3 attempts)
5. **Refund on Failure** - Automatic refund after max retries with audit trail

## Architecture

### Actor Hierarchy

```
Stage
├── BankSupervisor (supervisor)
├── AccountSupervisor (supervisor)
├── TransferSupervisor (supervisor)
└── Teller (supervised by BankSupervisor)
    └── Bank (supervised by BankSupervisor)
        ├── Account[1..N] (supervised by AccountSupervisor)
        │   └── TransactionHistory (child, supervised by AccountSupervisor)
        └── TransferCoordinator (supervised by TransferSupervisor)
```

### Supervision Strategy

All supervisors use **Resume** directive:
- **AccountSupervisor**: Handles business errors (insufficient funds, invalid amounts)
- **BankSupervisor**: Handles validation errors (invalid input, missing accounts)
- **TransferSupervisor**: Handles transfer errors (account lookup, deposit failures)

### Key Patterns

#### 1. Self-Messaging (TransactionHistory, TransferCoordinator)

```python
async def record_transaction(self, transaction: Transaction) -> None:
    """Self-send to ensure serialization through mailbox."""
    await self._self.append_transaction(transaction)

async def append_transaction(self, transaction: Transaction) -> None:
    """State change via mailbox (self-send only)."""
    self._transactions.append(transaction)
```

**Benefit**: All state changes serialized, preventing race conditions

#### 2. Parent-Child Relationships (Account → TransactionHistory)

```python
async def before_start(self) -> None:
    """Create child TransactionHistory actor."""
    self._transaction_history = self.child_actor_for(
        history_protocol,
        history_definition,
        'account-supervisor'  # Supervised by AccountSupervisor
    )
```

**Benefit**: Hierarchical shutdown, shared supervision strategy

#### 3. "Let It Crash" Philosophy (Teller)

```python
async def open_account(self, request: OpenAccountRequest) -> str:
    """Throws on invalid input - supervision handles errors."""
    initial_balance = float(request.initial_balance)  # May raise ValueError
    # ... validation throws errors, no try/catch
```

**Benefit**: Clean separation of business logic and error handling

#### 4. Context-Aware Error Messages

```python
# Set execution context before operation
teller.execution_context().reset() \
    .put_value('command', RequestType.OPEN_ACCOUNT.value) \
    .put_value('request', request)

# Supervisor extracts context for error formatting
command = execution_context.value_of('command')
request = execution_context.value_of('request')
explained = failure_explanation(error, command, request, ...)
```

**Benefit**: Detailed, user-friendly error messages with suggestions

## Running the Example

### Prerequisites

```bash
# From project root
cd examples/bank
```

### Start the Bank

```bash
python bank.py
```

### Example Session

```
Initializing DomoActors-Py Bank Actor System...
✅ Bank system initialized successfully!
   - Bank actor created
   - Teller actor created
   - Supervisors registered

============================================================
 DomoActors-Py Bank - Actor Model Banking System
============================================================
1. Open Account
2. Deposit Funds
3. Withdraw Funds
4. Transfer Funds
5. Account Summary
6. Transaction History
7. List All Accounts
8. Pending Transfers
0. Exit
============================================================

Enter your choice: 1
Owner name: Alice
Account type (checking/savings): checking
Initial balance: $1000
✅ Account opened successfully with account id: ACC123456
```

### Testing Error Handling

Try these scenarios to see supervision in action:

1. **Invalid Amount**
   ```
   Deposit: abc
   → Error caught by supervisor, detailed message shown
   ```

2. **Insufficient Funds**
   ```
   Withdraw: $10000 (more than balance)
   → Business error, handled by AccountSupervisor
   ```

3. **Transfer to Same Account**
   ```
   Transfer: ACC123 → ACC123
   → Validation error, caught by TransferSupervisor
   ```

4. **Failed Transfer Retry**
   - Open two accounts
   - Transfer funds
   - Observe retry attempts in logs
   - See automatic refund after max retries

## File Structure

```
bank/
├── bank.py                          # Interactive CLI menu
├── types.py                          # Shared data types
├── README.md                         # This file
├── model/
│   ├── bank_types.py                 # Actor protocol definitions
│   ├── account_actor.py              # Account implementation
│   ├── transaction_history_actor.py  # Transaction log (self-messaging)
│   ├── bank_actor.py                 # Root coordinator
│   ├── transfer_coordinator_actor.py # Transfer orchestration (retry logic)
│   └── teller_actor.py               # CLI validation layer
└── supervisors/
    ├── account_supervisor.py         # Account/History supervision
    ├── bank_supervisor.py            # Bank/Teller supervision
    ├── transfer_supervisor.py        # Transfer supervision
    └── failure_informant.py          # Error message formatter
```

## Transaction Flow Example

### Transfer: Account A → Account B ($100)

```
1. User: Transfer request via Teller
   ↓
2. Teller: Validates input, calls Bank.transfer()
   ↓
3. Bank: Delegates to TransferCoordinator
   ↓
4. TransferCoordinator:
   a. Withdraw $100 from Account A (synchronous)
      ✓ Success → Continue
      ✗ Failure → Stop transfer

   b. Self-send: recordPendingTransfer()
      Status: WITHDRAWN

   c. Self-send: attemptDeposit()
      Try deposit to Account B
      ✓ Success → completeTransfer() (COMPLETED)
      ✗ Failure → handleDepositFailure()

   d. (If deposit failed) Retry with backoff:
      Attempt 1: Wait 1s → attemptDeposit()
      Attempt 2: Wait 2s → attemptDeposit()
      Attempt 3: Wait 4s → attemptDeposit()

   e. (If max retries) processRefund():
      - Refund $100 to Account A
      - Record refund with reason in TransactionHistory
      - Status: REFUNDED
      - completeTransfer() (removes from pending)
```

## Learning Objectives

This example demonstrates:

1. **Hierarchical Actor Systems** - Parent-child relationships, shared supervision
2. **Message Passing** - Async communication, self-messaging for state consistency
3. **Supervision Strategies** - Resume directive, context-aware error handling
4. **State Machines** - Transfer coordination with retry logic
5. **Business Logic Separation** - Teller validates, Bank coordinates, Account manages
6. **Audit Trails** - Complete transaction history with refund tracking
7. **Fault Tolerance** - Retry with exponential backoff, automatic refunds
8. **Real-World Patterns** - Production-grade error handling and user experience

## Code Highlights

### Self-Messaging for State Consistency

```python
# TransactionHistoryActor
async def before_start(self) -> None:
    self._self = self.self_as()  # Get proxy for self-messaging

async def record_transaction(self, transaction: Transaction) -> None:
    await self._self.append_transaction(transaction)  # Via mailbox
```

### Retry with Exponential Backoff

```python
# TransferCoordinatorActor
if transfer.attempts < MAX_RETRY_ATTEMPTS:
    delay_ms = RETRY_DELAY_MS * (2 ** (transfer.attempts - 1))
    # Schedule retry: 1s, 2s, 4s
    self.scheduler().schedule_once(retry_task, delay_ms, 0)
```

### Context-Aware Error Formatting

```python
# Supervisors
def failure_explanation(cause, command, request, more_details, highlight):
    # Command-specific formatting
    if command == 'OpenAccount':
        lines.append(f"Owner: {request.owner}")
        lines.append(f"Suggestion: Ensure initial balance is valid")
    elif command == 'Transfer':
        lines.append(f"From: {request.from_account_number}")
        lines.append(f"To: {request.to_account_number}")
        lines.append(f"Suggestion: Ensure both accounts exist")
```

## Advanced Features

### Transaction Types

- `deposit` - Funds added
- `withdrawal` - Funds removed
- `transfer-in` - Received from transfer
- `transfer-out` - Sent via transfer
- `refund` - Returned after failed transfer

### Transfer States

- `withdrawn` - Funds taken from source, waiting for deposit
- `completed` - Successfully deposited to destination
- `failed-deposit` - Deposit failed after retries
- `refunded` - Funds returned to source with audit trail

## Comparison with TypeScript Version

This Python implementation is **functionally equivalent** to the TypeScript version:

✅ Same actor hierarchy and supervision structure
✅ Same 8 interactive commands
✅ Same transfer retry logic (3 attempts, exponential backoff)
✅ Same error handling philosophy ("let it crash")
✅ Same formatted output for CLI
✅ Same self-messaging patterns
✅ Same audit trail with refund tracking

**Key Differences**:
- Python uses `async/await` with asyncio (TypeScript uses Promises)
- Python uses `__init__` constructors (TypeScript uses constructors)
- Python uses dataclasses (TypeScript uses interfaces)
- Python uses dynamic protocol creation (TypeScript uses classes)

## Next Steps

1. **Experiment**: Try different error scenarios
2. **Extend**: Add new account types (money market, CD)
3. **Enhance**: Add interest calculation, account fees
4. **Scale**: Test with many concurrent transfers
5. **Monitor**: Add metrics and observability

## License

Licensed under the Reciprocal Public License 1.5

See LICENSE.md in repository root directory
