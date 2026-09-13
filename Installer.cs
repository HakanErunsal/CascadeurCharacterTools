using System;
using System.IO;
using System.Text;
using System.Windows.Forms;

internal static class MannyToolsInstaller
{
    private const string ProductName = "Manny Character Tools Installer";

    [STAThread]
    private static int Main(string[] args)
    {
        // Noninteractive mode exists only so the packaged installer can be verified.
        if (args.Length == 2 && args[0] == "--install")
        {
            try { InstallTo(args[1]); return 0; }
            catch (Exception error) { Console.Error.WriteLine(error); return 1; }
        }

        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        while (true)
        {
            using (FolderBrowserDialog picker = new FolderBrowserDialog())
            {
                picker.Description = "Select the Cascadeur folder that contains cascadeur.exe";
                picker.ShowNewFolderButton = false;
                string usualPath = @"D:\GameDevelopmentTools\Cascadeur";
                if (Directory.Exists(usualPath)) picker.SelectedPath = usualPath;

                if (picker.ShowDialog() != DialogResult.OK) return 0;
                string cascadeurFolder = picker.SelectedPath;
                if (!File.Exists(Path.Combine(cascadeurFolder, "cascadeur.exe")))
                {
                    MessageBox.Show(
                        "That folder does not contain cascadeur.exe. Please select the main Cascadeur installation folder.",
                        ProductName, MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    continue;
                }

                try
                {
                    InstallTo(cascadeurFolder);
                    MessageBox.Show(
                        "Installation completed.\n\nRestart Cascadeur, then open:\nScripts > Manny Tools > Character Panel",
                        ProductName, MessageBoxButtons.OK, MessageBoxIcon.Information);
                    return 0;
                }
                catch (UnauthorizedAccessException)
                {
                    MessageBox.Show(
                        "Windows denied access to that Cascadeur folder. Right-click Install.exe, choose Run as administrator, and select the folder again.",
                        ProductName, MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return 1;
                }
                catch (Exception error)
                {
                    MessageBox.Show("Installation failed:\n\n" + error.Message,
                        ProductName, MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return 1;
                }
            }
        }
    }

    private static void InstallTo(string cascadeurFolder)
    {
        string packageFolder = AppDomain.CurrentDomain.BaseDirectory;
        string sourceModule = Path.Combine(packageFolder, "upc_character_tools");
        string sourcePart = Path.Combine(packageFolder, "assets", "manny.partscasc");
        string scriptsRoot = Path.Combine(cascadeurFolder, "resources", "scripts");

        if (!File.Exists(Path.Combine(cascadeurFolder, "cascadeur.exe")))
            throw new InvalidOperationException("The selected folder does not contain cascadeur.exe.");
        if (!Directory.Exists(scriptsRoot))
            throw new InvalidOperationException("The selected Cascadeur installation has no resources\\scripts folder.");
        if (!Directory.Exists(sourceModule) || !File.Exists(sourcePart))
            throw new InvalidOperationException("Keep Install.exe beside the upc_character_tools and assets folders.");

        string targetModule = Path.Combine(scriptsRoot, "python", "upc_character_tools");
        string targetPartFolder = Path.Combine(scriptsRoot, "parts", "upc_character_tools");
        string targetMenu = Path.Combine(scriptsRoot, "python", "scripts", "upc_character_tools_menu");

        CopyDirectory(sourceModule, targetModule);
        Directory.CreateDirectory(targetPartFolder);
        File.Copy(sourcePart, Path.Combine(targetPartFolder, "manny.partscasc"), true);
        Directory.CreateDirectory(targetMenu);
        File.WriteAllText(Path.Combine(targetMenu, "__init__.py"), "", new UTF8Encoding(false));

        string loader =
            "def name():\r\n" +
            "    return 'Manny Tools.Character Panel'\r\n" +
            "def description():\r\n" +
            "    return 'Add named Manny characters and export normalized root-motion animations.'\r\n" +
            "def run(scene):\r\n" +
            "    import upc_character_tools\r\n" +
            "    upc_character_tools.show()\r\n";
        File.WriteAllText(Path.Combine(targetMenu, "character_panel.py"), loader, new UTF8Encoding(false));
    }

    private static void CopyDirectory(string source, string target)
    {
        Directory.CreateDirectory(target);
        foreach (string file in Directory.GetFiles(source))
            File.Copy(file, Path.Combine(target, Path.GetFileName(file)), true);
        foreach (string folder in Directory.GetDirectories(source))
        {
            if (String.Equals(Path.GetFileName(folder), "__pycache__", StringComparison.OrdinalIgnoreCase)) continue;
            CopyDirectory(folder, Path.Combine(target, Path.GetFileName(folder)));
        }
    }
}
