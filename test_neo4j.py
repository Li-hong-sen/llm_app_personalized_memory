"""测试 Neo4j 连接的诊断脚本"""
from neo4j import GraphDatabase
import sys

NEO4J_URI = "neo4j+s://7ebeea71.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = ""
NEO4J_DATABASE = "neo4j"

print(f"Python 版本: {sys.version}")
print(f"正在连接: {NEO4J_URI}")
print(f"用户名: {NEO4J_USERNAME}")
print(f"数据库: {NEO4J_DATABASE}")
print("-" * 50)

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    print("Driver 创建成功")
    
    # 验证连接
    driver.verify_connectivity()
    print("连接验证成功!")
    
    # 测试查询
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run("RETURN 1 AS num")
        record = result.single()
        print(f"测试查询成功: {record['num']}")
    
    driver.close()
    print("Neo4j 连接完全正常!")
    
except Exception as e:
    print(f"连接失败!")
    print(f"错误类型: {type(e).__name__}")
    print(f"错误信息: {e}")
    
    # 额外诊断
    import traceback
    print("\n完整错误栈:")
    traceback.print_exc()

