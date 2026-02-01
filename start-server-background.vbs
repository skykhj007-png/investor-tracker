Set WshShell = CreateObject("WScript.Shell")

' Start Cloudflare Tunnel
WshShell.Run """C:\Users\k\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe"" tunnel run investor-tracker", 0, False

' Wait 3 seconds
WScript.Sleep 3000

' Start Streamlit
WshShell.CurrentDirectory = "C:\Users\k\investor-tracker"
WshShell.Run "cmd /c python -m streamlit run src/web/dashboard.py --server.port 8501 --server.headless true", 0, False
