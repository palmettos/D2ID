using DiabloInterface.D2.Struct;
using DiabloInterface.Logging;
using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Pipes;
using System.Text;
using System.Threading;

namespace DiabloInterface.Server
{
    class ItemServer
    {
        string pipeName;
        Thread listenThread;
        D2DataReader dataReader;

        public ItemServer(D2DataReader dataReader, string pipeName)
        {
            this.dataReader = dataReader;
            this.pipeName = pipeName;

            listenThread = new Thread(new ThreadStart(ServerListen));
            listenThread.IsBackground = true;
            listenThread.Start();
        }

        public void Stop()
        {
            if (listenThread != null)
            {
                listenThread.Abort();
                listenThread = null;
            }
        }

        void ServerListen()
        {
            var ps = new PipeSecurity();
            System.Security.Principal.SecurityIdentifier sid = new System.Security.Principal.SecurityIdentifier(System.Security.Principal.WellKnownSidType.BuiltinUsersSid, null);
            ps.AddAccessRule(new PipeAccessRule(sid, PipeAccessRights.ReadWrite, System.Security.AccessControl.AccessControlType.Allow));

            while (true)
            {
                NamedPipeServerStream pipe = null;
                try
                {
                    pipe = new NamedPipeServerStream(pipeName,
                        PipeDirection.InOut, 1,
                        PipeTransmissionMode.Message,
                        PipeOptions.Asynchronous,
                        1024, 1024, ps);
                    pipe.WaitForConnection();
                    Thread clientConnectionHandler = new Thread(new ParameterizedThreadStart(HandleClientConnection)) { IsBackground = true };
                    clientConnectionHandler.Start(pipe);
                    if (!clientConnectionHandler.Join(1000))
                    {
                        clientConnectionHandler.Abort();
                        Console.WriteLine("Connection handler timeout reached");
                        Logger.Instance.WriteLine("Client connection handler timed out in item server thread...");
                    }
                    pipe.Close();
                }
                catch (UnauthorizedAccessException e)
                {
                    // note: should only come here if another pipe with same name is already open (= another instance of d2interface is running)
                    Logger.Instance.WriteLine("Error: {0}", e.Message);
                    Thread.Sleep(1000); // try again in 1 sec to prevent tool from lagging
                }
                catch (IOException e)
                {
                    Logger.Instance.WriteLine("ItemServer Error: {0}", e.Message);

                    if (pipe != null) pipe.Close();
                }
                catch (Exception e)
                {
                    Console.WriteLine(e.Message);
                    Logger.Instance.WriteLine("Other exception: {0}", e.Message);
                }
            }
        }

        void HandleClientConnection(Object pipeObject)
        {
            try
            {
                NamedPipeServerStream pipe = (NamedPipeServerStream)pipeObject;
                var reader = new JsonStreamReader(pipe, Encoding.UTF8);
                var request = reader.ReadJson<QueryRequest>();

                QueryResponse response = new QueryResponse();
                var equipmentLocations = GetItemLocations(request);

                dataReader.ItemSlotAction(equipmentLocations, (itemReader, item) =>
                {
                    ItemQuality quality = itemReader.GetItemQuality(item);
                    string color = null;
                    switch (quality)
                    {
                        case ItemQuality.Low:
                        case ItemQuality.Normal:
                        case ItemQuality.Superior:
                            color = "WHITE";
                            break;
                        case ItemQuality.Magic:
                            color = "BLUE";
                            break;
                        case ItemQuality.Rare:
                            color = "YELLOW";
                            break;
                        case ItemQuality.Crafted:
                        case ItemQuality.Tempered:
                            color = "ORANGE";
                            break;
                        case ItemQuality.Unique:
                            color = "GOLD";
                            break;
                        case ItemQuality.Set:
                            color = "GREEN";
                            break;
                    }

                    ItemResponse data = new ItemResponse();
                    data.ItemName = itemReader.GetFullItemName(item);
                    data.BaseItem = itemReader.GetGrammaticalName(itemReader.GetItemName(item), out string grammerCase);
                    data.Quality = color;
                    data.Properties = itemReader.GetMagicalStrings(item);
                    data.Location = itemReader.GetItemData(item)?.BodyLoc ?? BodyLocation.None;
                    response.Items.Add(data);
                });

                response.IsValid = equipmentLocations.Count > 0;
                response.Success = response.Items.Count > 0;
                var writer = new JsonStreamWriter(pipe, Encoding.UTF8);
                writer.WriteJson(response);
                writer.Flush();
            }
            catch (Exception e)
            {
                Console.WriteLine(e.Message);
                Logger.Instance.WriteLine("exception caught in HandleClientConnection:");
                Logger.Instance.WriteLine(e.Message);
                return;
            }
        }

        List<BodyLocation> GetItemLocations(QueryRequest request)
        {
            List<BodyLocation> locations = new List<BodyLocation>();
            if (string.IsNullOrEmpty(request.EquipmentSlot))
                return locations;

            var name = request.EquipmentSlot.ToLowerInvariant();
            switch (name)
            {
                case "helm":
                case "head":
                    locations.Add(BodyLocation.Head);
                    break;
                case "armor":
                case "body":
                case "torso":
                    locations.Add(BodyLocation.BodyArmor);
                    break;
                case "amulet":
                    locations.Add(BodyLocation.Amulet);
                    break;
                case "ring":
                case "rings":
                    locations.Add(BodyLocation.RingLeft);
                    locations.Add(BodyLocation.RingRight);
                    break;
                case "belt":
                    locations.Add(BodyLocation.Belt);
                    break;
                case "glove":
                case "gloves":
                case "hand":
                    locations.Add(BodyLocation.Gloves);
                    break;
                case "boot":
                case "boots":
                case "foot":
                case "feet":
                    locations.Add(BodyLocation.Boots);
                    break;
                case "primary":
                case "weapon":
                    locations.Add(BodyLocation.PrimaryLeft);
                    break;
                case "offhand":
                case "shield":
                    locations.Add(BodyLocation.PrimaryRight);
                    break;
                case "weapon2":
                case "secondary":
                    locations.Add(BodyLocation.SecondaryLeft);
                    break;
                case "secondaryshield":
                case "secondaryoffhand":
                case "shield2":
                    locations.Add(BodyLocation.SecondaryRight);
                    break;
                default: break;
            }

            return locations;
        }
    }
}
