// Kuji (Куджи) — нативный запускатель приложения.
//
// Назначение: дать инженеру обычный двойной клик по Kuji.exe с фирменной
// иконкой, не превращая поставку в монолит. Скрипты приложения, встроенная
// среда runtime\python и все ресурсы остаются на диске в виде дерева файлов
// (как и сейчас для run_app.cmd), а этот exe только находит своё окружение и
// запускает main.py без окна консоли.
//
// Почему C#/ .NET Framework 4: компилятор csc.exe есть в каждой Windows 10/11
// (C:\Windows\Microsoft.NET\Framework64\v4.0.30319), сборка не требует ни
// Visual Studio, ни pip, ни интернета; среда выполнения .NET 4.8 встроена в
// Windows, поэтому на машине заказчика такой exe работает «из коробки».
//
// Иконка вшивается при сборке ключом /win32icon (см. build_exe.cmd), поэтому
// Kuji.exe красиво выглядит и в проводнике, и на панели задач.
//
// Запуск: build_exe.cmd -> Kuji.exe в корне проекта.

using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace KujiLauncher
{
    internal static class Program
    {
        // Точка входа. Окна консоли у такого exe нет (сборка /target:winexe).
        [STAThread]
        private static void Main(string[] args)
        {
            // Каталог, в котором лежит сам Kuji.exe. Всё остальное
            // (main.py, runtime\, assets\, eta\) ищем относительно него, а не
            // относительно текущего каталога: ярлык и проводник могут прийти
            // из любого места.
            string appDir = AppDomain.CurrentDomain.BaseDirectory;
            string mainPy = Path.Combine(appDir, "main.py");

            if (!File.Exists(mainPy))
            {
                Fail(appDir,
                    "Не найден файл запуска main.py рядом с Kuji.exe.\n\n" +
                    "Положите Kuji.exe в корень папки приложения или " +
                    "используйте run_app.cmd.");
                return;
            }

            // Интерпретатор из встроенного окружения. pythonw (без консоли)
            // предпочтителен; python.exe — запасной, если поставка собрана
            // без pythonw.
            string[] candidates =
            {
                Path.Combine(appDir, "runtime", "python", "pythonw.exe"),
                Path.Combine(appDir, "runtime", "python", "python.exe"),
            };

            string python = null;
            foreach (string candidate in candidates)
            {
                if (File.Exists(candidate))
                {
                    python = candidate;
                    break;
                }
            }

            if (python == null)
            {
                Fail(appDir,
                    "Не найдено встроенное окружение Python:\n" +
                    Path.Combine(appDir, "runtime", "python") + "\n\n" +
                    "Похоже, папка скопирована не полностью: каталог runtime " +
                    "не входит в репозиторий и разворачивается отдельно.");
                return;
            }

            try
            {
                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = python;
                // Кавычки обязательны: путь может содержать пробелы и кириллицу.
                psi.Arguments = BuildArguments(mainPy, args);
                // Рабочий каталог = корень приложения, как у run_app.cmd.
                psi.WorkingDirectory = appDir;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;

                Process.Start(psi);
            }
            catch (Exception ex)
            {
                Fail(appDir, "Не удалось запустить приложение:\n\n" + ex.Message);
            }
        }

        // Собираем строку запуска: main.py плюс всё, что передали Kuji.exe
        // (например, путь к .kuji.json из ассоциации файлов).
        private static string BuildArguments(string mainPy, string[] args)
        {
            System.Text.StringBuilder sb = new System.Text.StringBuilder();
            sb.Append('"').Append(mainPy).Append('"');
            if (args != null)
            {
                foreach (string arg in args)
                {
                    if (string.IsNullOrEmpty(arg))
                    {
                        continue;
                    }
                    sb.Append(" \"").Append(arg.Replace("\"", "\\\"")).Append('"');
                }
            }
            return sb.ToString();
        }

        // Ошибка показывается по-русски и в модальном окне: инженер видит её
        // даже при запуске двойным кликом, где консоль недоступна.
        private static void Fail(string appDir, string text)
        {
            MessageBox.Show(text, "Kuji (Куджи)",
                MessageBoxButtons.OK, MessageBoxIcon.Warning);
            Debug.WriteLine("Kuji launcher: " + appDir + " — " + text);
        }
    }
}
