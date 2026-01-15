
import os
import functools
from typing import Optional, Callable
from openinference.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.trace import get_tracer_provider, Status, StatusCode
from opentelemetry import trace

from config import Config

# Global tracer instance
_tracer = None


def init_tracing() -> Optional[object]:
    """Initialize Phoenix tracing if configured"""
    global _tracer

    if not Config.PHOENIX_ENABLED:
        return None

    try:
        try:
            from phoenix.otel import register
        except Exception as e:
            print(f"Phoenix tracing unavailable: {e}")
            return None

        # Get configuration from Config class
        api_key = Config.PHOENIX_API_KEY
        endpoint = Config.PHOENIX_ENDPOINT
        project_name = Config.PHOENIX_PROJECT_NAME

        # Configure Phoenix client headers if API key is provided
        if api_key:
            os.environ["PHOENIX_CLIENT_HEADERS"] = f"api_key={api_key}"
            print("Phoenix API key configured successfully")
        else:
            print("Warning: No API key provided - may not be able to connect to Phoenix cloud")

        # Register Phoenix tracer provider
        tracer_provider = register(
            project_name=project_name,
            endpoint=endpoint,
            auto_instrument=True  # Enable automatic instrumentation
        )

        # Instrument OpenAI SDK for tracing
        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

        # Initialize global tracer
        _tracer = tracer_provider.get_tracer("acc_system")

        print(f"Phoenix tracing initialized successfully for project: {project_name}")
        return tracer_provider

    except Exception as e:
        print(f"Phoenix tracing initialization failed: {e}")
        print("Continuing without Phoenix tracing...")
        return None


def trace_method(span_name: Optional[str] = None, log_result: bool = False):
    """Decorator to trace method execution with Phoenix

    Args:
        span_name: Custom span name (default: function name)
        log_result: If True, log the result object to span attributes (default: False)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # If tracing is not initialized, execute the original function directly
            if not _tracer:
                return func(*args, **kwargs)

            # Generate span name
            name = span_name or f"{func.__name__}"

            # Create tracing span
            with _tracer.start_as_current_span(name) as span:
                try:
                    # Add basic attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)

                    # Execute original function
                    result = func(*args, **kwargs)

                    # Set span status to OK
                    span.set_status(Status(StatusCode.OK))
                    span.set_attribute("function.success", True)

                    # Log result if requested
                    if log_result and result is not None:
                        try:
                            # Handle Pydantic models
                            if hasattr(result, 'model_dump'):
                                result_dict = result.model_dump()
                            elif hasattr(result, 'dict'):
                                result_dict = result.dict()
                            elif isinstance(result, dict):
                                result_dict = result
                            else:
                                result_dict = {"value": str(result)}

                            # Log result as JSON string
                            import json
                            span.set_attribute("function.result", json.dumps(result_dict, default=str))
                        except Exception as e:
                            span.set_attribute("function.result_error", f"Failed to log result: {e}")

                    return result

                except Exception as e:
                    # Set span status to ERROR
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("function.success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        return wrapper
    return decorator
