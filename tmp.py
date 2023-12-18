import os
import sys


async def response():
    file_name = "data.xlsx"
    file_path = "/tmp/"

    with open(file_path + file_name, "rb") as f:
        tmp_file = f.read() # Считали локальный файл

    headers = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Disposition": "attachment; filename=" + file_name,
    }

    resp = web.StreamResponse(headers=headers)
    resp.content_length = sys.getsizeof(tmp_file)
    resp.content_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    await resp.write(tmp_file) # Записали данные в обьект
    os.remove(file_path + file_name) # Удалили локальный файл
    return resp
