using System.Collections.Generic;
using DiabloInterface.D2.Struct;

namespace DiabloInterface.Server
{
    class ItemResponse
    {
        public string ItemName { get; set; }
        public string BaseItem { get; set; }
        public string Quality { get; set; }
        public BodyLocation Location { get; set; }
        public List<string> Properties { get; set; }

        public ItemResponse()
        {
            Properties = new List<string>();
        }
    }

    class QueryResponse
    {
        public bool IsValid { get; set; }
        public bool Success { get; set; }
        public List<ItemResponse> Items { get; set; }

        public QueryResponse()
        {
            Items = new List<ItemResponse>();
        }
    }
}
