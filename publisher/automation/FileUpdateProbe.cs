// Public release gate: actual packaged runtime, anonymous downloads, signed apply/rollback.
using System;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using Ecuss.Desktop;

internal sealed class FileUpdateHandler : DelegatingHandler
{
    public int Requests;
    public FileUpdateHandler() : base(new HttpClientHandler { AllowAutoRedirect = false, UseCookies = false, UseDefaultCredentials = false }) { }
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancel)
    {
        if (request.Headers.Authorization != null || request.Headers.Contains("Cookie") || !PublicDownload.AllowedRedirect(request.RequestUri) || request.RequestUri.AbsolutePath.EndsWith(".ecuss-update.zip", StringComparison.Ordinal))
            throw new InvalidOperationException("Unexpected credential, destination or full package download.");
        Requests++;
        return base.SendAsync(request, cancel);
    }
}
internal static class FileUpdateProbe
{
    static int checks;
    static void Check(bool value, string name) { if (!value) throw new Exception(name); checks++; Console.WriteLine("PASS " + name); }
    static async Task<int> Main(string[] args)
    {
        bool production = args.Length == 4;
        string proof = File.ReadAllText(args[2]), previous = production ? File.ReadAllText(args[3]) : null;
        var catalog = production ? SignedUpdates.Verify(proof, previous, DateTimeOffset.UtcNow).catalog : Json.Read<UpdateCatalog>(proof);
        var old = PackagePolicy.VerifyDirectory(args[0]); var target = PackagePolicy.VerifyDirectory(args[1]);
        var package = catalog.packages.Single(p => p.profile == old.profile);
        string work = Path.Combine(Path.GetTempPath(), "ecuss-file-probe-" + Guid.NewGuid().ToString("N")); Directory.CreateDirectory(work);
        try
        {
            Check(package.fileUpdate != null && target.profile == DistributionProfile.Id, "paired file-update descriptor and runtime profile");
            var handler = new FileUpdateHandler();
            string cache = Path.Combine(work, "cache"), stage = Path.Combine(work, "stage");
            FileUpdatePlan plan; Release next;
            using (var client = new HttpClient(handler) { Timeout = TimeSpan.FromMinutes(5) })
            {
                plan = await FileUpdates.FetchPlan(client, package, catalog.modules, args[0], cache, CancellationToken.None);
                Check(PackagePolicy.HashFile(Path.Combine(cache, "index.json")) == package.fileUpdate.sha256, "anonymous index matches signed digest");
                next = await FileUpdates.Assemble(package, catalog.modules, args[0], cache, stage, client, null, CancellationToken.None);
            }
            Check(handler.Requests > 0, "anonymous file requests completed without full ZIP");
            Check(PackagePolicy.HashFile(Path.Combine(stage, "manifest.json")) == PackagePolicy.HashFile(Path.Combine(args[1], "manifest.json")), "assembled manifest equals reviewed full package");
            Check(next.files.All(f => PackagePolicy.HashFile(PackagePolicy.Inside(stage, f.path)) == f.sha256), "all assembled files have approved target hashes");
            Check(next.releaseId == target.releaseId && next.appVersion == target.appVersion, "assembled release identity matches target");
            Check(PackagePolicy.VerifyDirectory(args[0]).releaseId == old.releaseId, "active source release unchanged");
            var transferred = Directory.GetFiles(cache).Sum(f => new FileInfo(f).Length);
            Check(transferred <= plan.downloadBytes + package.fileUpdate.bytes, "download cache contains only required file objects and index");
            OnlinePackage.VerifyRelease(next, package, catalog.modules);
            Check(next.profile == old.profile && next.modules.Length == target.modules.Length, "module and profile validation preserved");
            Console.WriteLine("FILE_DOWNLOAD_CHECKS=" + checks);
            Console.WriteLine("FILE_DOWNLOAD_BYTES=" + transferred + "; FULL_BYTES=" + package.bytes + "; REUSED=" + plan.reusedFiles);
            if (production)
            {
                int before = checks; var store = new ReleaseStore(Path.Combine(work, "data")); store.InstallSeed(args[0]);
                File.WriteAllText(Path.Combine(store.Root, "synthetic-settings.txt"), "settings");
                File.WriteAllText(Path.Combine(store.Root, "synthetic-result.txt"), "result");
                string id = Guid.NewGuid().ToString("N"), pendingCache = FileUpdates.DirectoryPath(store.Root, id); Directory.CreateDirectory(pendingCache);
                foreach (string file in Directory.GetFiles(cache)) File.Copy(file, Path.Combine(pendingCache, Path.GetFileName(file)));
                AtomicFile.Write(SignedUpdates.CachePath(store.Root), previous);
                AtomicFile.Write(OnlinePackage.PendingPath(store.Root), Json.Write(new PendingUpdate { id = id, fromRelease = old.releaseId, package = package, modules = catalog.modules, signedEnvelope = proof, transfer = FileUpdates.Mode }));
                string apply = Path.Combine(work, "apply"); var extracted = OnlinePackage.ExtractPending(store.Root, old, apply);
                Check(extracted.releaseId == target.releaseId, "production signature validates pending file update at application time");
                store.Commit(apply, extracted, "online-update");
                Check(store.ReadState().active == target.releaseId && store.ReadState().previous == old.releaseId, "signed file update atomically activates target");
                store.Rollback(); Check(store.ReadState().active == old.releaseId, "signed update rollback restores predecessor");
                Check(File.ReadAllText(Path.Combine(store.Root, "synthetic-settings.txt")) == "settings", "settings preserved");
                Check(File.ReadAllText(Path.Combine(store.Root, "synthetic-result.txt")) == "result", "business results preserved");
                Console.WriteLine("SIGNED_FILE_APPLY_CHECKS=" + (checks - before));
            }
        }
        finally { Directory.Delete(work, true); }
        return 0;
    }
}
