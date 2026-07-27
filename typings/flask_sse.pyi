# coding=utf-8
from __future__ import unicode_literals

from flask import Blueprint
from redis import StrictRedis
from typing import Any, Generator

__version__: str = "1.0.0"

class Message(object):
    """
    Data that is published as a server-sent event.
    """
    def __init__(
        self,
        data: Any,
        type: str | None = None,
        id: str | None = None,
        retry: int | None = None,
    ) -> None:
        """
        Create a server-sent event.

        :param data: The event data. If it is not a string, it will be
            serialized to JSON using the Flask application's
            :class:`~flask.json.JSONEncoder`.
        :param type: An optional event type.
        :param id: An optional event ID.
        :param retry: An optional integer, to specify the reconnect time for
            disconnected clients of this stream.
        """
        ...

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize this object to a minimal dictionary, for storing in Redis.
        """
        ...

    def __str__(self) -> str:
        """
        Serialize this object to a string, according to the `server-sent events
        specification <https://www.w3.org/TR/eventsource/>`_.
        """
        ...

    def __repr__(self) -> str: ...
    def __eq__(self, other: Any) -> bool: ...

class ServerSentEventsBlueprint(Blueprint):
    """
    A :class:`flask.Blueprint` subclass that knows how to publish, subscribe to,
    and stream server-sent events.
    """
    @property
    def redis(self) -> StrictRedis:
        """
        A :class:`redis.StrictRedis` instance, configured to connect to the
        current application's Redis server.
        """
        ...

    def publish(
        self,
        data: Any,
        type: str | None = None,
        id: str | None = None,
        retry: int | None = None,
        channel: str = "sse",
    ) -> Any:
        """
        Publish data as a server-sent event.

        :param data: The event data. If it is not a string, it will be
            serialized to JSON using the Flask application's
            :class:`~flask.json.JSONEncoder`.
        :param type: An optional event type.
        :param id: An optional event ID.
        :param retry: An optional integer, to specify the reconnect time for
            disconnected clients of this stream.
        :param channel: If you want to direct different events to different
            clients, you may specify a channel for this event to go to.
            Only clients listening to the same channel will receive this event.
            Defaults to "sse".
        """
        ...

    def messages(self, channel: str = "sse") -> Generator[Message, None, None]:
        """
        A generator of :class:`~flask_sse.Message` objects from the given channel.
        """
        ...

    def stream(self) -> Any:
        """
        A view function that streams server-sent events. Ignores any
        :mailheader:`Last-Event-ID` headers in the HTTP request.
        Use a "channel" query parameter to stream events from a different
        channel than the default channel (which is "sse").
        """
        ...

sse: ServerSentEventsBlueprint
"""
An instance of :class:`~flask_sse.ServerSentEventsBlueprint`
that hooks up the :meth:`~flask_sse.ServerSentEventsBlueprint.stream`
method as a view function at the root of the blueprint. If you don't
want to customize this blueprint at all, you can simply import and
use this instance in your application.
"""
