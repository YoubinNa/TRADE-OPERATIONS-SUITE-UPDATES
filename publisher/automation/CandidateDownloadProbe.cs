// Runs against an immutable published Desktop assembly; does not activate an unsigned update.
using System;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using Ecuss.Desktop;
internal sealed class AnonymousOnlyHandler : DelegatingHandler
{
    public int Requests;
    public AnonymousOnlyHandler() : base(new HttpClientHandler { AllowAutoRedirect=false, UseCookies=false, UseDefaultCredentials=false }) {}
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancel)
    {
        if(request.Headers.Authorization!=null || request.Headers.Contains("Cookie") || !PublicDownload.AllowedRedirect(request.RequestUri))
            throw new InvalidOperationException("Unexpected credential or download destination.");
        Requests++;
        return base.SendAsync(request,cancel);
    }
}
internal static class CandidateDownloadProbe
{
    static int checks;
    static void Check(bool value,string name){if(!value)throw new Exception(name);checks++;Console.WriteLine("PASS "+name);}
    static async Task<int> Main(string[] args)
    {
        var installed=PackagePolicy.VerifyDirectory(args[0]);
        var registry=Json.Read<RepositoryRegistry>(File.ReadAllText(Path.Combine(args[0],"module-sources.json")));
        var catalog=Json.Read<UpdateCatalog>(File.ReadAllText(args[1]));
        var package=catalog.packages.Single(x=>x.profile=="master");
        OnlinePackage.Validate(package,registry);
        Check(installed.profile=="master" && package.appVersion==catalog.appVersion,"actual Master assembly validates candidate metadata");
        var work=Path.Combine(Path.GetTempPath(),"ecuss-public-download-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(work);
        try{
            var handler=new AnonymousOnlyHandler();
            using(var client=new HttpClient(handler){Timeout=TimeSpan.FromMinutes(3)})
            using(var response=await PublicDownload.Open(client,package,CancellationToken.None)){
                Check(response.StatusCode==HttpStatusCode.OK,"actual public Release download HTTP 200");
                Check(handler.Requests>=1 && handler.Requests<=6,"all download/redirect requests anonymous and allowlisted");
                using(var stream=await response.Content.ReadAsStreamAsync())
                    await OnlinePackage.Copy(stream,Path.Combine(work,"download.zip"),package,null,CancellationToken.None);
            }
            Check(new FileInfo(Path.Combine(work,"download.zip")).Length==package.bytes && PackagePolicy.HashFile(Path.Combine(work,"download.zip"))==package.sha256,"complete download exact length and SHA-256");
            var extracted=PackagePolicy.ExtractZip(Path.Combine(work,"download.zip"),Path.Combine(work,"unpacked"));
            OnlinePackage.VerifyRelease(extracted,package,catalog.modules);
            Check(extracted.appVersion==catalog.appVersion && extracted.modules.Length==catalog.modules.Length,"downloaded payload integrity and exact approved modules");
            Check(!Directory.Exists(Path.Combine(work,"unpacked","modules","balance-ecuss")),"personal mail assets absent");
            bool rejected=false;try{SignedUpdates.Verify("{}",null,DateTimeOffset.UtcNow);}catch(InvalidDataException){rejected=true;}
            Check(rejected,"unsigned metadata remains rejected; no stable/pending activation in this test");
        }finally{Directory.Delete(work,true);}
        Console.WriteLine("Checks: "+checks+"; actual production download code; signature/application acceptance still separate.");return 0;
    }
}
