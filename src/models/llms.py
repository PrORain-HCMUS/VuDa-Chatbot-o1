from langchain_openai import ChatOpenAI
from langchain_experimental.agents import create_pandas_dataframe_agent
import pandas as pd


def load_llm(model_name):
    """Load Large Language Model.

    Args:
        model_name (str): The name of the model to load.

    Raises:
        ValueError: If the model_name is not recognized.

    Returns:
        ChatOpenAI: An instance of ChatOpenAI configured for the specified model.
    """

    if model_name == "gpt-3.5-turbo":
        return ChatOpenAI(
            model=model_name,
            temperature=0.0,
            max_tokens=1000,
        )
    elif model_name == "gpt-4":
        return ChatOpenAI(
            model=model_name,
            temperature=0.0,
            max_tokens=1000,
        )
    elif model_name == "gemini-pro":
        # Import Gemini and Return Gemini mode
        pass
    else:
        raise ValueError(
            "Unknown model.\
                Please choose from ['gpt-3.5-turbo','gpt-4', ...]"
        )


def create_agent_from_csv(model_name, csv_path, return_steps=False):
    df = pd.read_csv(csv_path)
    llm = load_llm(model_name)
    return create_pandas_dataframe_agent(
        llm,
        df,
        verbose=True,
        handle_parsing_errors=True,
        agent_type="tool-calling",
        allow_dangerous_code=True,
        return_intermediate_steps=return_steps
    )
