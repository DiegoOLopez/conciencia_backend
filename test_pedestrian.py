import asyncio
from schemas.request import RouteRequest, Coordinate, TravelPriority
from agents.pedestrian import pedestrian_agent
from datetime import datetime

async def main():
    req = RouteRequest(
        origin=Coordinate(lat=19.4326, lon=-99.1332),
        destination=Coordinate(lat=19.4346, lon=-99.1352),
        departure_time=datetime.now(),
        transport_modes=["WALK"],
        priority=TravelPriority.ACCESSIBLE
    )
    res = await pedestrian_agent.calculate_routes(req)
    print(res)

asyncio.run(main())
