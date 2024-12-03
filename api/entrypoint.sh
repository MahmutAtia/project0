#!/bin/sh
if [ "$DEBUG" = "1" ]; then
    uvicorn main:app --host 0.0.0.0 --port 80 --reload
else
    uvicorn main:app --host 0.0.0.0 --port 80
fi
