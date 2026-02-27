using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;
using Emgu.CV;
using Emgu.CV.CvEnum;
using Emgu.CV.Structure;

namespace AutoClickerBoomBang;

public class MainForm : Form
{
    // --- Native imports ---
    [DllImport("user32.dll")] static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] static extern void mouse_event(uint dwFlags, int dx, int dy, uint dwData, int dwExtraInfo);
    [DllImport("user32.dll")] static extern bool GetCursorPos(out POINT lpPoint);
    const uint MOUSEEVENTF_LEFTDOWN = 0x02;
    const uint MOUSEEVENTF_LEFTUP = 0x04;

    [StructLayout(LayoutKind.Sequential)]
    struct POINT { public int X, Y; }

    // --- State ---
    readonly List<TargetImage> _targets = new();
    volatile bool _running;
    Thread? _scanThread;
    int _clicks;

    // --- UI ---
    ListBox _targetsList = null!;
    TrackBar _thresholdSlider = null!;
    Label _thresholdLabel = null!;
    NumericUpDown _intervalInput = null!;
    NumericUpDown _delayInput = null!;
    Button _startBtn = null!;
    Label _statusLabel = null!;
    Label _clicksLabel = null!;

    record TargetImage(string Name, Mat Image);

    public MainForm()
    {
        Text = "🎮 AutoClicker BoomBang";
        Size = new Size(460, 560);
        FormBorderStyle = FormBorderStyle.FixedSingle;
        MaximizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(26, 26, 46);
        ForeColor = Color.FromArgb(224, 224, 224);
        Font = new Font("Segoe UI", 10);

        BuildUI();
    }

    void BuildUI()
    {
        var title = new Label
        {
            Text = "🎮 AutoClicker BoomBang",
            Font = new Font("Segoe UI", 15, FontStyle.Bold),
            ForeColor = Color.FromArgb(0, 212, 170),
            AutoSize = true, Location = new Point(110, 12)
        };
        Controls.Add(title);

        // --- Targets ---
        var targetsLabel = new Label { Text = "🎯 Imágenes objetivo:", Location = new Point(15, 50), AutoSize = true };
        Controls.Add(targetsLabel);

        _targetsList = new ListBox
        {
            Location = new Point(15, 75), Size = new Size(415, 85),
            BackColor = Color.FromArgb(22, 33, 62), ForeColor = Color.FromArgb(224, 224, 224),
            BorderStyle = BorderStyle.FixedSingle
        };
        Controls.Add(_targetsList);

        var addBtn = MakeButton("➕ Añadir", new Point(15, 168), 130);
        addBtn.Click += (_, _) => AddTargets();
        Controls.Add(addBtn);

        var removeBtn = MakeButton("🗑️ Quitar", new Point(155, 168), 130);
        removeBtn.Click += (_, _) => RemoveTarget();
        Controls.Add(removeBtn);

        // --- Settings ---
        var settingsLabel = new Label
        {
            Text = "⚙️ Configuración",
            Font = new Font("Segoe UI", 10, FontStyle.Bold),
            ForeColor = Color.FromArgb(0, 212, 170),
            Location = new Point(15, 210), AutoSize = true
        };
        Controls.Add(settingsLabel);

        // Threshold
        Controls.Add(new Label { Text = "Sensibilidad:", Location = new Point(15, 240), AutoSize = true });
        _thresholdSlider = new TrackBar
        {
            Minimum = 50, Maximum = 95, Value = 75, TickFrequency = 5,
            Location = new Point(160, 235), Size = new Size(200, 30),
            BackColor = Color.FromArgb(26, 26, 46)
        };
        _thresholdSlider.ValueChanged += (_, _) => _thresholdLabel.Text = $"{_thresholdSlider.Value}%";
        Controls.Add(_thresholdSlider);

        _thresholdLabel = new Label { Text = "75%", Location = new Point(365, 240), AutoSize = true };
        Controls.Add(_thresholdLabel);

        // Scan interval
        Controls.Add(new Label { Text = "Escaneo cada (ms):", Location = new Point(15, 280), AutoSize = true });
        _intervalInput = new NumericUpDown
        {
            Minimum = 50, Maximum = 5000, Value = 300, Increment = 50,
            Location = new Point(200, 278), Size = new Size(80, 28),
            BackColor = Color.FromArgb(22, 33, 62), ForeColor = Color.FromArgb(224, 224, 224)
        };
        Controls.Add(_intervalInput);

        // Click delay
        Controls.Add(new Label { Text = "Pausa entre clicks (ms):", Location = new Point(15, 318), AutoSize = true });
        _delayInput = new NumericUpDown
        {
            Minimum = 10, Maximum = 2000, Value = 150, Increment = 50,
            Location = new Point(200, 316), Size = new Size(80, 28),
            BackColor = Color.FromArgb(22, 33, 62), ForeColor = Color.FromArgb(224, 224, 224)
        };
        Controls.Add(_delayInput);

        // --- Start/Stop ---
        _startBtn = new Button
        {
            Text = "▶️  INICIAR", Location = new Point(15, 370), Size = new Size(415, 50),
            Font = new Font("Segoe UI", 13, FontStyle.Bold),
            BackColor = Color.FromArgb(0, 212, 170), ForeColor = Color.FromArgb(26, 26, 46),
            FlatStyle = FlatStyle.Flat, Cursor = Cursors.Hand
        };
        _startBtn.FlatAppearance.BorderSize = 0;
        _startBtn.Click += (_, _) => Toggle();
        Controls.Add(_startBtn);

        // --- Status ---
        _statusLabel = new Label
        {
            Text = "⏸️ Parado", Location = new Point(15, 430),
            Font = new Font("Segoe UI", 10, FontStyle.Bold),
            ForeColor = Color.FromArgb(255, 204, 0), AutoSize = true
        };
        Controls.Add(_statusLabel);

        _clicksLabel = new Label
        {
            Text = "Clicks: 0", Location = new Point(15, 455), AutoSize = true
        };
        Controls.Add(_clicksLabel);

        var tip = new Label
        {
            Text = "💡 Pulsa F6 o mueve ratón a esquina sup-izq = parada de emergencia",
            Location = new Point(15, 490), AutoSize = true,
            ForeColor = Color.FromArgb(100, 100, 100), Font = new Font("Segoe UI", 8)
        };
        Controls.Add(tip);

        // Global hotkey F6 to stop
        KeyPreview = true;
        KeyDown += (_, e) => { if (e.KeyCode == Keys.F6) Stop(); };
    }

    Button MakeButton(string text, Point loc, int width) => new()
    {
        Text = text, Location = loc, Size = new Size(width, 32),
        BackColor = Color.FromArgb(22, 33, 62), ForeColor = Color.FromArgb(224, 224, 224),
        FlatStyle = FlatStyle.Flat, Cursor = Cursors.Hand
    };

    void AddTargets()
    {
        using var ofd = new OpenFileDialog
        {
            Title = "Selecciona imágenes de los objetos",
            Filter = "Imágenes|*.png;*.jpg;*.jpeg;*.bmp",
            Multiselect = true
        };
        if (ofd.ShowDialog() != DialogResult.OK) return;

        foreach (var file in ofd.FileNames)
        {
            try
            {
                var mat = CvInvoke.Imread(file, ImreadModes.Color);
                if (mat.IsEmpty) { MessageBox.Show($"No se pudo cargar: {Path.GetFileName(file)}"); continue; }
                var name = Path.GetFileName(file);
                _targets.Add(new TargetImage(name, mat));
                _targetsList.Items.Add($"  {name} ({mat.Width}x{mat.Height}px)");
            }
            catch (Exception ex) { MessageBox.Show($"Error: {ex.Message}"); }
        }
    }

    void RemoveTarget()
    {
        var idx = _targetsList.SelectedIndex;
        if (idx < 0) return;
        _targets[idx].Image.Dispose();
        _targets.RemoveAt(idx);
        _targetsList.Items.RemoveAt(idx);
    }

    void Toggle()
    {
        if (_running) Stop();
        else Start();
    }

    void Start()
    {
        if (_targets.Count == 0) { MessageBox.Show("Añade al menos una imagen objetivo."); return; }
        _running = true;
        _clicks = 0;
        UpdateUI("🔍 Escaneando...", "⏹️  PARAR", Color.FromArgb(248, 81, 73));

        var threshold = _thresholdSlider.Value / 100.0;
        var interval = (int)_intervalInput.Value;
        var delay = (int)_delayInput.Value;

        _scanThread = new Thread(() => ScanLoop(threshold, interval, delay)) { IsBackground = true };
        _scanThread.Start();
    }

    void Stop()
    {
        _running = false;
        UpdateUI("⏸️ Parado", "▶️  INICIAR", Color.FromArgb(0, 212, 170));
    }

    void UpdateUI(string status, string btnText, Color btnColor)
    {
        if (InvokeRequired) { Invoke(() => UpdateUI(status, btnText, btnColor)); return; }
        _statusLabel.Text = status;
        _startBtn.Text = btnText;
        _startBtn.BackColor = btnColor;
    }

    void UpdateClicks()
    {
        if (InvokeRequired) { Invoke(UpdateClicks); return; }
        _clicksLabel.Text = $"Clicks: {_clicks}";
    }

    void ScanLoop(double threshold, int interval, int delay)
    {
        while (_running)
        {
            try
            {
                // Failsafe: cursor at top-left corner
                if (GetCursorPos(out var pt) && pt.X <= 5 && pt.Y <= 5)
                {
                    _running = false;
                    UpdateUI("🛑 Failsafe — parado", "▶️  INICIAR", Color.FromArgb(0, 212, 170));
                    return;
                }

                // Capture all screens
                foreach (var screen in Screen.AllScreens)
                {
                    if (!_running) return;

                    var bounds = screen.Bounds;
                    using var bmp = new Bitmap(bounds.Width, bounds.Height, PixelFormat.Format24bppRgb);
                    using (var g = Graphics.FromImage(bmp))
                        g.CopyFromScreen(bounds.Left, bounds.Top, 0, 0, bounds.Size);

                    using var screenMat = bmp.ToMat();

                    foreach (var target in _targets)
                    {
                        if (!_running) return;

                        using var result = new Mat();
                        CvInvoke.MatchTemplate(screenMat, target.Image, result, TemplateMatchingType.CcoeffNormed);

                        // Find all matches above threshold
                        var resultData = new float[result.Rows * result.Cols];
                        Marshal.Copy(result.DataPointer, resultData, 0, resultData.Length);

                        for (int y = 0; y < result.Rows; y++)
                        {
                            for (int x = 0; x < result.Cols; x++)
                            {
                                if (!_running) return;
                                if (resultData[y * result.Cols + x] >= threshold)
                                {
                                    int cx = bounds.Left + x + target.Image.Width / 2;
                                    int cy = bounds.Top + y + target.Image.Height / 2;

                                    ClickAt(cx, cy);
                                    _clicks++;
                                    UpdateClicks();
                                    Thread.Sleep(delay);

                                    // Skip nearby pixels to avoid double-clicking same spot
                                    x += target.Image.Width;
                                }
                            }
                        }
                    }
                }

                Thread.Sleep(interval);
            }
            catch (Exception)
            {
                Thread.Sleep(500);
            }
        }
    }

    static void ClickAt(int x, int y)
    {
        SetCursorPos(x, y);
        Thread.Sleep(15);
        mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0);
        Thread.Sleep(10);
        mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0);
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        _running = false;
        base.OnFormClosing(e);
    }
}

static class BitmapExtensions
{
    public static Mat ToMat(this Bitmap bmp)
    {
        var rect = new Rectangle(0, 0, bmp.Width, bmp.Height);
        var data = bmp.LockBits(rect, ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb);
        var mat = new Mat(bmp.Height, bmp.Width, Emgu.CV.CvEnum.DepthType.Cv8U, 3);
        var bytes = new byte[data.Stride * data.Height];
        Marshal.Copy(data.Scan0, bytes, 0, bytes.Length);

        // Handle stride mismatch
        if (data.Stride == mat.Step)
            Marshal.Copy(bytes, 0, mat.DataPointer, bytes.Length);
        else
        {
            for (int row = 0; row < bmp.Height; row++)
                Marshal.Copy(bytes, row * data.Stride, mat.DataPointer + row * mat.Step, mat.Width * 3);
        }

        bmp.UnlockBits(data);
        return mat;
    }
}
