import subprocess
import sys
import argparse
from pathlib import Path

def fetch_dependencies(package_name, max_depth, repo_url):
    """
    Собирает зависимости для указанного пакета с заданной глубиной.

    :param package_name: Имя анализируемого пакета.
    :param max_depth: Максимальная глубина анализа зависимостей.
    :param repo_url: URL-адрес репозитория (не используется в apt-cache, но может быть полезен для расширений).
    :return: Словарь, где ключи — пакеты, а значения — множества их зависимостей.
    """
    dependencies = {}  # Словарь для хранения зависимостей
    visited = set()  # Набор посещенных пакетов, чтобы избежать циклов

    def get_deps(package, current_depth):
        """
        Рекурсивно находит зависимости для пакета до заданной глубины.

        :param package: Текущий анализируемый пакет.
        :param current_depth: Текущая глубина анализа.
        """
        if current_depth > max_depth or package in visited:
            return
        visited.add(package)  # Помечаем пакет как посещенный
        # Запускаем команду apt-cache depends для получения зависимостей
        result = subprocess.run(
            ['apt-cache', 'depends', package],
            capture_output=True, text=True
        )
        lines = result.stdout.splitlines()
        package_deps = set()
        for line in lines:
            if line.strip().startswith('Depends:'):
                dep = line.split('Depends:')[1].strip()  # Извлекаем имя зависимости
                package_deps.add(dep)
        dependencies[package] = package_deps
        # Рекурсивно обрабатываем каждую найденную зависимость
        for dep in package_deps:
            get_deps(dep, current_depth + 1)

    get_deps(package_name, 1)  # Начинаем с глубины 1
    return dependencies

def build_puml_graph(dependencies):
    """
    Генерирует содержимое PlantUML на основе зависимостей.

    :param dependencies: Словарь зависимостей, где ключ — пакет, а значение — его зависимости.
    :return: Строка с содержимым PlantUML.
    """
    graph = "@startuml\n"
    for package, deps in dependencies.items():
        for dep in deps:
            graph += f'"{package}" --> "{dep}"\n'  # Добавляем стрелки для каждой зависимости
    graph += "@enduml"
    return graph

def save_puml_file(puml_content, file_path):
    """
    Сохраняет содержимое PlantUML в файл.

    :param puml_content: Строка с содержимым PlantUML.
    :param file_path: Путь к файлу, в который будет сохранен результат.
    """
    with open(file_path, 'w') as file:
        file.write(puml_content)  # Записываем содержимое в файл

def render_graph(puml_path, output_path, plantuml_path):
    """
    Выполняет визуализацию графа с использованием PlantUML.

    :param puml_path: Путь к файлу .puml.
    :param output_path: Путь к выходному PNG файлу.
    :param plantuml_path: Путь к исполняемому файлу PlantUML.
    """
    result = subprocess.run(
        [plantuml_path, puml_path, '-tpng', '-o', str(output_path.parent)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        # Если PlantUML завершился с ошибкой, выводим сообщение и завершаем работу
        print(f"Error during PlantUML rendering: {result.stderr}", file=sys.stderr)
        sys.exit(1)

def main():
    """
    Главная функция для парсинга аргументов и выполнения анализа зависимостей.
    """
    parser = argparse.ArgumentParser(description='Dependency graph visualizer for Ubuntu packages.')
    parser.add_argument('--plantuml_path', required=True, help='Path to PlantUML jar or executable.')
    parser.add_argument('--package', required=True, help='Name of the package to analyze.')
    parser.add_argument('--output', required=True, type=Path, help='Output path for the PNG file.')
    parser.add_argument('--depth', type=int, default=3, help='Max depth of dependency analysis.')
    parser.add_argument('--repo', default='http://archive.ubuntu.com/ubuntu', help='Repository URL.')

    args = parser.parse_args()  # Парсим аргументы командной строки

    # Получаем зависимости для указанного пакета
    dependencies = fetch_dependencies(args.package, args.depth, args.repo)

    if not dependencies:
        print(f"No dependencies found for package {args.package}", file=sys.stderr)
        sys.exit(1)

    # Генерируем содержимое PlantUML
    puml_content = build_puml_graph(dependencies)

    # Сохраняем содержимое PlantUML в файл
    puml_path = args.output.with_suffix('.puml')
    save_puml_file(puml_content, puml_path)

    # Визуализируем граф с помощью PlantUML
    render_graph(puml_path, args.output, args.plantuml_path)

    print(f"Graph successfully saved to {args.output}")  # Сообщаем об успешной генерации графа

if __name__ == "__main__":
    main()
