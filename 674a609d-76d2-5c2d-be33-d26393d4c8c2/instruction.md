# Evolve the result backends, the worker pipeline and the messaging surface

The repository is pinned at a revision that predates a later release. Your task is to make the
behaviour that release describes appear, without regressing the 3144 tests that already pass. The
objectives below are the release's own scope restated. They are numbered for reference only.

You are not given the release tag, any pull request number, or any diff. Derive the change list from
the objectives and the repository.

This repository keeps its tests in a separate top-level `t/` tree, outside the package you are
changing. Change only files under `celery/`, and do not modify `t/`: the whole tree is replaced with
the later release's version before your work is exercised, so edits to it have no effect.

**This task is broad rather than deep.** The work spans 17 files and 20 behavioural areas, and no
single area dominates. There is no single insight that carries it; there are nineteen mostly
independent pieces of work, and four of them rest on a single test each.

The disclosed-interfaces table below carries the names this release invents, which is more than a
task like this would normally give away.
Eight of them are configuration settings, and the reason is that a setting name is pure convention:
nothing in this repository implies `control_queue_durable` over `control_durable_queue`, and a solver
that picks the second writes correct behaviour no test can reach. The other six are a changed
parameter list, two new members on the consumer, an event primitive and a module constant. Read the
disclosed signatures in that table carefully — two of them insert parameters in the MIDDLE of an existing list, and
callers in this repository pass those positionally.

Everything else must be derived from the repository and from what the tests assert.

## Disclosed interfaces

Every symbol below is created by this release and appears nowhere in the source tree you
received, so no amount of reading could recover its name. The suite imports each exactly as
written: correct behaviour behind a different name or arity does not satisfy them. Symbols this
release changes that ALREADY exist in your tree are deliberately not listed; find those yourself.
A name on its own is not enough: each symbol must carry the behaviour described below.

| Module | Symbol | Parameters | Returns |
| --- | --- | --- | --- |
| `celery.worker.consumer.consumer` | `cancel_active_requests` | self | cancels every request the consumer currently has in flight. Takes no arguments beyond self. |
| `celery.worker.consumer.consumer` | `broker_connection_retry_attempt` | (attribute, not a method) | an attribute on the consumer tracking which reconnection attempt is in progress. It is read, not called. |
| `celery.worker.request` | `cancel` | self, pool, signal, emit_retry | cancels the request. `emit_retry` is NEW and is appended as the last parameter. It controls whether cancelling publishes a retry for the task rather t |
| `celery.app.amqp` | `Queues` | self, queues, create_missing=None, create_missing_queue_type=None, create_missing_queue_exchange_type=None, autoexchange=None, max_priority=None | the queue registry. Two parameters are NEW and both are inserted directly after `create_missing`, BEFORE `autoexchange` and `max_priority`. The positi |
| `celery.app.defaults` | `control_queue_durable` | Option(False, type='bool') | a boolean setting, default False. When true the control mailbox queues are declared durable. Exposed to application code as `app.conf.control_queue_durable`, and reached by the suite through the config namespace rather than by import. |
| `celery.app.defaults` | `control_queue_exclusive` | Option(False, type='bool') | a boolean setting, default False. When true the control mailbox queues are declared exclusive. Note durability and exclusivity are SEPARATE settings rather than one mode, and both default False. |
| `celery.app.defaults` | `event_queue_durable` | Option(False, type='bool') | a boolean setting, default False, the event-queue counterpart of control_queue_durable. The event namespace carries its OWN pair of settings; it does not inherit the control pair. |
| `celery.app.defaults` | `event_queue_exclusive` | Option(False, type='bool') | a boolean setting, default False, the event-queue counterpart of control_queue_exclusive. |
| `celery.app.defaults` | `task_create_missing_queue_type` | Option('classic', type='string') | a string setting whose default is the literal 'classic'. Selects the queue type declared when a task names a queue that does not exist. |
| `celery.app.defaults` | `task_create_missing_queue_exchange_type` | Option(None, type='string') | a string setting defaulting to None, selecting the exchange type for that auto-created queue. Unlike its sibling above this one DOES default to None, meaning fall back to the existing behaviour. |
| `celery.app.defaults` | `worker_disable_prefetch` | Option(False, type='bool') | a boolean setting, default False. When true the worker fetches no more messages than it can currently execute. Also surfaced as a command-line flag on the worker entry point. |
| `celery.app.defaults` | `worker_eta_task_limit` | Option(None, type='int') | an integer setting defaulting to None, meaning unbounded. Caps how many ETA or countdown tasks a worker will hold in memory at once. |
| `celery.worker.consumer.consumer` | `Consumer.cancel_active_requests` | self | cancels every request the consumer currently has in flight. Takes no arguments beyond self. |
| `celery.worker.consumer.consumer` | `Consumer.broker_connection_retry_attempt` | (attribute, not a method) | an attribute on the consumer tracking which reconnection attempt is in progress. It is read, not called. |
| `celery.backends.asynchronous` | `EventletAdaptedEvent` | class with methods: is_set(self), set(self), wait(self, timeout) | an event primitive presenting the threading.Event interface over an eventlet-compatible wait, so result-backend waiting behaves the same under a green-thread pool. `wait` takes a `timeout` positionally. |
| `celery.worker.consumer.delayed_delivery` | `RETRIED_EXCEPTIONS` | (module-level constant) | the tuple of exception types whose occurrence during native delayed-delivery setup is retried rather than fatal. A module-level name the suite reaches directly. |

## Objectives

**1. A chord that fails reports why.** When a task inside a chord raises, the result backend must turn
that failure into a chord error carrying the original cause, dispatch it to the right callback whether
that callback is a single task or a group, and clean up without letting a second exception raised
during cleanup mask the first. This covers errbacks, a chord body holding several tasks, a cause that
is not an exception at all, and no cause at all. The machinery needs its own way to build a stand-in
request for the failed task, honouring basic parameters, defaults, and extra parameters when given.
This is the largest objective, thirteen tests, and the rest of the backend work hangs off it.

**2. A worker that does not prefetch.** Add the ability to stop the worker fetching more messages than
it can currently execute. It is off by default, it is settable on the command line as well as in
configuration, and when it is on the number of messages in flight must respect both the autoscaler's
maximum concurrency and the limit on reserved requests.

**3. Cancelling work already in flight.** Give the consumer a way to cancel every request it is
currently running, leaving tasks that already succeeded untouched. Cancelling an individual request
grows a parameter controlling whether the cancellation publishes a retry for the task or simply
terminates it; both paths are tested.

**4. Reconnection reports which attempt it is on.** While the consumer retries a broker connection,
the attempt in progress must be observable rather than implicit.

**5. Django connections and caches close cleanly.** The framework integration's worker fixup must close
database connections on the right schedule and at worker-process start, and whether it closes a pooled
connection must follow the relevant framework setting rather than being assumed. Closing a connection
pool that is already gone raises a lookup error that must be suppressed; a failure closing the cache,
by contrast, must propagate.

**6. Delayed-delivery setup retries a broker that is not ready.** Binding the queues for native
delayed delivery must retry on a defined set of transient exceptions rather than treating the first
failure as fatal, continue past a single queue's failure where it can, and surface the failure when it
cannot. The retry helper must handle a backoff value returned as a float, and the topic-exchange path
must start.

**7. The Redis client is named and can be given a credential provider.** The Redis result backend must
set a client name when one is configured and leave it alone when not, and must accept a credential
provider supplied either in the connection URL or through configuration.

**8. A Redis-backed chord counts its parts correctly.** The path that runs when one part of a chord
returns must behave for both settings of the option that governs it.

**9. A request terminates on failure and on timeout.** The two paths that should terminate a running
request must do so, without emitting the event or logging the error they currently do.

**10. A chord body always has a task identity.** When a chord runs, its body must end up with a valid
task id even when none was supplied from outside, rather than failing later on an empty id. Freezing
the body is what assigns it.

**11. Parent and root identity through a direct apply.** Applying a task directly must thread task,
parent and root ids correctly, including a nested parent-and-child call and a parent that has no root
id of its own.

**12. The queue created for an unknown route.** When a task names a queue that does not exist and the
application is configured to create it, the kind of queue created becomes configurable, as does the
exchange type used for it. It must be settable both through configuration and as an explicit
parameter, and the quorum case must work.

**13. The application timezone resolves predictably.** Using the local timezone, and the case where
resolving the local zone fails, must each behave as the tests assert.

**14. Bounding how many future-dated tasks a worker holds.** Add a limit on how many ETA or countdown
tasks a worker will hold at once. The prefetch count the worker negotiates must reflect the limit when
it is set — including when it is set to zero, which is not the same as unset.

**15. The control mailbox declares its queues.** The control queues gain settings selecting whether
they are declared durable and whether they are declared exclusive. Some combinations are not coherent,
and an incoherent one must be rejected rather than silently accepted.

**16. Event timestamps in the dumper.** The event dumper's output must carry the timestamp in the
expected form, for a task event and for a non-task event.

**17. Event queues declare their own durability.** The event queues gain their own independent pair of
durable and exclusive settings, with validation. The event namespace does not inherit the control
namespace's pair.

**18. A corrupted beat schedule is survivable.** When the persistent scheduler's stored schedule
cannot be unpickled, it must recover rather than propagate the unpickling error.

**19. Forgetting a result removes it from pending.** Forgetting an asynchronous result must also drop
it from the backend's pending set.

Objectives 2, 3, 12, 14, 15 and 17 add capability, and most of their names are disclosed. The rest
change conduct behind interfaces that already exist, and for those you must read what the tests
assert.

Two traps are worth stating because measurement found them.

The settings in objectives 12, 15 and 17 are read during queue declaration, which happens on paths
that hundreds of otherwise unrelated tests traverse. Getting a setting NAME wrong does not fail
quietly — it fails several hundred tests that have nothing to do with the objective.

Objective 1 introduces two private names that the release's own test module imports directly. Until
both exist, that module cannot be imported at all. Defining them as bare stubs will make the module
load, but restoring collection is not the same as changing behaviour. Required behaviour is what
matters, not the presence of the names.

## Constraints

Change only files under `celery/`. Do not modify the `t/` tree; it is restored from the release
before your work is exercised, so edits to it have no effect.

Complete objectives rather than spreading partial repairs across all of them. A change that
satisfies one objective by breaking another is not an improvement.
