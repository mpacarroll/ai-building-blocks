# Widget Service Spec

The service MUST accept a POST to /widgets with a JSON body.
The service MUST reject a body larger than 1 megabyte with HTTP 413.
The service SHALL return the created widget id within 200 milliseconds.
It is REQUIRED that every widget id is a version-4 UUID.
