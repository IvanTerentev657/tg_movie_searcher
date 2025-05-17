import os
import re
import sys
import time

from dotenv import load_dotenv

from openai import AsyncOpenAI

from duckduckgo_search import DDGS


class AiSearcher:
    """
    Асинхронный клиент для поиска фильмов через OpenRouter DeepSeek API и генерации ответов на основе LLM.
    """

    def __init__(self, api_key_env: str = "OPENROUTER_API_KEY", base_url: str = "https://openrouter.ai/api/v1")->None:
        load_dotenv()
        api_key = os.getenv(api_key_env)
        if not api_key:
            print(f"ERROR: {api_key_env} not set")
            sys.exit(1)
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        self.current_model: str = "deepseek/deepseek-chat:free"

    async def list_models(self, key_words: list[str]| None = None) -> list[str]:
        """
        Выводит все доступные модели, содержащие все ключевые слова.
        """
        key_words = key_words or []
        models = []
        all_models = await self.client.models.list()
        for m in all_models.data:
            if all(key in m.id for key in key_words):
                models.append(m.id)
        return models

    async def set_model(self, model: str):
        model_list = await self.list_models()
        if model in model_list:
            self.current_model = model

    @staticmethod
    async def get_movie_link(title: str) -> str:
    try:
        request = f"Фильм {title.upper()} смотреть онлайн"

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(lambda: next(search(request, num_results=1, unique=True), None))
    except Exception:
        return "❗️Ссылка не найдена"

    @staticmethod
    def get_only_title_prompt(query) -> str:
        prompt = (
                f"Найди полное название фильма по запросу: \"{query}\"?\n"
                f"Ответь в формате: название фильма и больше ничего\n"
                f"Строго следуй формату, не пиши ничего лишнего, не смей галюцинировать и придумывать название"
        )
        return prompt

    @staticmethod
    def get_title_and_description_prompt(query) -> str:
        prompt = (
            "Ты ассистент, который на основании запроса пользователя даёт:\n"
            "1) На ПЕРВОЙ строке — ТОЛЬКО название фильма в одинарных [квадратных скобках]\n"
            "2) На второй — краткое описание\n\n"
            f"Пользователь ищет «{query}» — сформируй ответ в нужном формате."
        )
        return prompt

    async def get_movie_info(self, movie: str, model: str | None = None) -> str:
        """
        Возвращает описание фильма и ссылку по заданному запросу и модели.
        """
        model = model or self.current_model

        prompt = self.get_title_and_description_prompt(movie)

        print(prompt)
        resp = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Отвечай быстро и точно в соответствии с форматом"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            stream=False,
            tools=[]
        )
        print('\n'+str(resp))

        answer = resp.choices[0].message.content.strip().split('\n', 1)

        match = re.search(r"\[(.*?)\]", answer[0]) if answer else None
        title = match.group(1) if match else answer[0] if answer else ""
        while title and (title[0] == '[' or title[-1] == ']'):
            title = title.lstrip('[').rstrip(']')

        description = answer[1] if len(answer) > 1 else ""

        link = await self.get_movie_link(title)

        return "\n".join(["«"+title+"»", description, link])

    async def benchmark(self, movie: str, models_to_test: list[str]) -> None:
        """
        Проводит замер времени отклика для списка моделей и выводит результаты.
        """
        print(f"Benchmark for movie query: «{movie}»\n")
        for model in models_to_test:
            start = time.perf_counter()
            answer = await self.get_movie_info(movie, model=model)
            elapsed = time.perf_counter() - start
            print(f"Model: {model}")
            print(f" Time: {elapsed:.2f} sec")
            print(f" Answer: {answer}\n{'-' * 60}")


# class InternetSearcher:


async def main():
    # pass
    searcher = AiSearcher()

    # models = await searcher.list_models(["deepseek", "free"])
    # print("\n".join(models))

    # res = await searcher.get_movie_link('Покемон: Фильм первый — Мьюту наносит ответный удар')
    # print(res)

    # result = await searcher.get_movie_info("шоу про мужчину за которым следят")
    # print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
