from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class BountyJob:

    victim_id: str
    killer_id: str
    reward: int
    created_tick: int
    fulfilled: bool = False
    fulfilled_by: str | None = None
    fulfilled_tick: int | None = None

class BountyBoard:

    def __init__(self) -> None:
        self._jobs: list[BountyJob] = []

    def post(self, victim_id: str, killer_id: str, reward: int, tick: int) -> BountyJob:

        existing = self.open_bounty_for(killer_id)
        if existing is not None:
            existing.victim_id = victim_id
            existing.reward = reward
            existing.created_tick = tick
            return existing

        job = BountyJob(
            victim_id=victim_id,
            killer_id=killer_id,
            reward=reward,
            created_tick=tick,
        )
        self._jobs.append(job)
        return job

    def fulfill(self, killer_id: str, hunter_id: str, tick: int) -> BountyJob | None:

        job = self.open_bounty_for(killer_id)
        if job is None:
            return None
        job.fulfilled = True
        job.fulfilled_by = hunter_id
        job.fulfilled_tick = tick
        return job

    def open_bounty_for(self, killer_id: str) -> BountyJob | None:

        for job in self._jobs:
            if job.killer_id == killer_id and not job.fulfilled:
                return job
        return None

    def is_wanted(self, agent_id: str) -> bool:

        return self.open_bounty_for(agent_id) is not None

    def open_jobs(self) -> list[BountyJob]:
        return [j for j in self._jobs if not j.fulfilled]

    def all_jobs(self) -> list[BountyJob]:
        return list(self._jobs)

    def to_dict(self) -> list[dict]:
        return [
            {
                "victim_id": j.victim_id,
                "killer_id": j.killer_id,
                "reward": j.reward,
                "created_tick": j.created_tick,
                "fulfilled": j.fulfilled,
                "fulfilled_by": j.fulfilled_by,
                "fulfilled_tick": j.fulfilled_tick,
            }
            for j in self._jobs
        ]
