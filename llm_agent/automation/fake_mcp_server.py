from __future__ import annotations

import argparse

from fastmcp import FastMCP

MOVIE_ID = "movie-1"


def recommendation_server() -> FastMCP:
    server = FastMCP("Agent smoke recommendation MCP")

    @server.tool()
    async def recommendation_get_movies(
        limit: int = 3,
        preference: str | None = None,
        traceparent: str | None = None,
        tracestate: str | None = None,
        correlation_id: str | None = None,
        request_id: str | None = None,
        demo_fault: str | None = None,
    ) -> dict[str, object]:
        return {
            "ok": True,
            "recommendations": [
                {
                    "id": "recommendation-1",
                    "title": "The Type-Safe Matinee",
                    "movie_reservation_movie_id": MOVIE_ID,
                }
            ][:limit],
        }

    return server


def reservation_server() -> FastMCP:
    server = FastMCP("Agent smoke reservation MCP")

    @server.tool()
    async def reservation_get_catalog(
        movie_id: str | None = None,
        traceparent: str | None = None,
        tracestate: str | None = None,
        correlation_id: str | None = None,
        request_id: str | None = None,
        demo_fault: str | None = None,
    ) -> dict[str, object]:
        selected_movie_id = movie_id or MOVIE_ID
        return {
            "ok": True,
            "catalog": {
                "movies": [{"id": selected_movie_id, "title": "The Type-Safe Matinee"}],
                "screenings": [
                    {
                        "id": "screening-1",
                        "movieId": selected_movie_id,
                        "seats": [
                            {"id": "seat-1", "row": "A", "number": 1},
                            {"id": "seat-2", "row": "A", "number": 2},
                        ],
                    }
                ],
            },
        }

    @server.tool()
    async def reservation_request_seats(
        screening_id: str,
        seat_ids: list[str],
        traceparent: str | None = None,
        tracestate: str | None = None,
        correlation_id: str | None = None,
        request_id: str | None = None,
        demo_fault: str | None = None,
    ) -> dict[str, object]:
        return {
            "ok": True,
            "reservation_request": {"id": "request-1", "status": "REQUESTED"},
        }

    @server.tool()
    async def reservation_get_request_status(
        reservation_request_id: str,
        traceparent: str | None = None,
        tracestate: str | None = None,
        correlation_id: str | None = None,
        request_id: str | None = None,
        demo_fault: str | None = None,
    ) -> dict[str, object]:
        return {
            "ok": True,
            "found": True,
            "reservation_request": {"id": reservation_request_id, "status": "CONFIRMED"},
            "reservation": {"id": "reservation-1"},
        }

    return server


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("component", choices=("recommendation", "reservation"))
    args = parser.parse_args()

    if args.component == "recommendation":
        server, port = recommendation_server(), 8092
    else:
        server, port = reservation_server(), 8091
    server.run(transport="http", host="127.0.0.1", port=port, path="/mcp")


if __name__ == "__main__":
    main()
