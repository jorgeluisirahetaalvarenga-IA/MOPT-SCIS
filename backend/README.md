# SCIS - Sistema de Control de Inventario 
 
## Prueba T�cnica LeaderTeam 
 
### Tecnolog�as 
- Python 3.x + FastAPI 
- SQLAlchemy 2.0 + SQLite 
- Uvicorn 
 
### Requerimientos implementados 
1. ? GET /api/products - Listado con paginaci�n 
2. ? POST /api/inventory/movement - Control de concurrencia 
3. ? Prevencion de stock negativo 
4. ? Auditoria completa de movimientos 
 
### Instalaci�n 
\`\`\`bash 
# 1. Activar entorno virtual 
call venv\Scripts\activate.bat 
 
# 2. Inicializar base de datos 
python scripts\init_database.py 
 
# 3. Ejecutar aplicaci�n 
uvicorn app.main:app --reload 
\`\`\` 
 
### Endpoints 
- \`GET /\` - Informaci�n del sistema 
- \`GET /api/products\` - Listar productos 
- \`POST /api/inventory/movement\` - Registrar movimiento 
- \`GET /docs\` - Documentaci�n Swagger 

