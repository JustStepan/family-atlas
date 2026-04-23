tags = ['tata', '#roro']

tags = [f'#{t}' for t in tags if not t.startswith('#')]
print(tags)