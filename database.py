import motor.motor_asyncio

motorClient = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://Phidipedes:CybbIhDtophSWD9UJaEqQeNlGEaFY4J5@omnis.w0ty6.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")

omnisDB = motorClient["omnis"]
trialsCollection = omnisDB["trials"]
memberCollection = omnisDB["members"]
activityCollection = omnisDB["activity"]