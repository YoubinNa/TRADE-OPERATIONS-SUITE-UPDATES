using System;
using System.IO;
using System.Reflection;
using System.Threading.Tasks;
using Ecuss.Desktop;

// Uses the exact distributed Host. No credentials, response bodies or business
// records are printed. The remote transport is explicitly read-only.
internal static class RecordsConnectionProbe
{
    private static async Task Run(string root)
    {
        var assembly = typeof(RecordSync).Assembly;
        var flags = BindingFlags.Instance | BindingFlags.NonPublic;
        var type = assembly.GetType("Ecuss.Desktop.WorkRecordsClient", true);
        var client = Activator.CreateInstance(type, flags, null,
            new object[] { root, new Release { profile = DistributionProfile.Id }, null }, null);
        try
        {
            var loaded = type.GetField("remote", flags).GetValue(client);
            if (loaded == null) throw new IOException("Packaged connection unavailable.");
            var remoteType = loaded.GetType();
            var token = (string)remoteType.GetField("token", flags).GetValue(loaded);
            var transport = (IRecordRemote)Activator.CreateInstance(remoteType, new object[] { token, false, false });
            using ((IDisposable)transport)
            {
                await transport.Clock();
                var sync = new RecordSync(transport);
                foreach (var company in RecordsPolicy.Companies)
                {
                    await sync.Read(company);
                    Console.WriteLine("RECORDS_READ_OK=" + company);
                }
            }
        }
        finally { ((IDisposable)client).Dispose(); }
    }
    private static int Main(string[] args)
    {
        try { Run(args[0]).GetAwaiter().GetResult(); Console.WriteLine("RECORDS_LIVE_CHECKS=2"); return 0; }
        catch (Exception e)
        {
            var property = e.GetType().GetProperty("StatusCode", BindingFlags.Instance | BindingFlags.NonPublic);
            Console.WriteLine("RECORDS_LIVE_FAILED=" + (property == null ? "connection" : "http_" + property.GetValue(e, null)));
            return 1;
        }
    }
}
