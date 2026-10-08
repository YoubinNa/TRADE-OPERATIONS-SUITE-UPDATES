using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using Ecuss.Desktop;
class SupabaseBootstrapProbe
{
 static int Main(string[] args)
 {
  try {
   var assembly=typeof(PackagePolicy).Assembly;
   if(assembly.GetManifestResourceNames().Contains("records.bootstrap"))throw new Exception("Legacy credential resource forbidden.");
   byte[] raw;using(var stream=assembly.GetManifestResourceStream("supabase.bootstrap"))using(var copy=new MemoryStream()){if(stream==null)throw new Exception("Missing public configuration.");stream.CopyTo(copy);raw=copy.ToArray();}
   if(raw.Length>4096)throw new Exception("Unexpected configuration size.");
   string hash;using(var sha=SHA256.Create())hash=BitConverter.ToString(sha.ComputeHash(raw)).Replace("-","").ToLowerInvariant();
   if(args.Length!=2||hash!=args[1])throw new Exception("Unapproved public configuration.");
   var c=Json.Read<Dictionary<string,object>>(Encoding.UTF8.GetString(raw));
   if(c.Count!=3||!c.ContainsKey("schema")||!c.ContainsKey("url")||!c.ContainsKey("publishableKey")||Convert.ToInt32(c["schema"])!=1)throw new Exception("Invalid public configuration schema.");
   if((string)c["url"]!=args[0]||!Regex.IsMatch((string)c["url"],"^https://[a-z0-9]{20}\\.supabase\\.co$"))throw new Exception("Unexpected project.");
   if(!Regex.IsMatch((string)c["publishableKey"],"^sb_publishable_[A-Za-z0-9_-]{16,200}$"))throw new Exception("Non-public key rejected.");
   Console.WriteLine("SUPABASE_BOOTSTRAP_OK");return 0;
  }catch(Exception e){Console.Error.WriteLine(e.GetType().Name);return 1;}
 }
}
